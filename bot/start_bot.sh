#!/bin/bash

APPDIR="/Users/skv/Documents/safeEat/bot"
PIDFILE="$APPDIR/safeeat.pid"
PID=

func_running() {
  if [ -s "$PIDFILE" ]; then
    PID=`cat "$PIDFILE" 2>/dev/null`
    if [ -n "$PID" ]; then
      if kill -0 $PID 2>/dev/null ; then
       return 0
      fi
    fi
  fi
  return 1
}


func_status() {
  if func_running ; then
    echo "bot running"
    return 0
  fi
  echo "bot not running"
  return 1
}


func_stop() {
  if func_running && [ -n "$PID" ] ; then
    echo -n "stopping bot..."
    if kill $PID 2>/dev/null ; then
      while kill -0 $PID 2>/dev/null ; do sleep 1 ; done
      echo -ne "\033[60G" ; echo "done"
      return 0
    else
      echo -ne "\033[60G" ; echo "failed"
    fi
  else
    echo "bot not running"
  fi
  return 1
}


func_start() {
  echo -n "starting bot..."
  . /Users/skv/Documents/safeEat/bot/venv/bin/activate
  python $APPDIR/cli.py --run  --d #2>&1
  # python $APPDIR/cli.py --run #2>&1
  deactivate
  sleep 1
  if func_running ; then
    echo -ne "\033[60G" ; echo "done"
    return 0
  else
    echo -ne "\033[60G" ; echo "failed"
    return 1
  fi
}


func_restart() {
  func_stop
  func_start
}


case "$1" in
  start)  func_start ;;
  stop)   func_stop  >&2 ;;
  restart)  func_restart  ;;
  status)   func_status  >&2 ;;
  *)
     echo "Usage: $0 start | stop | restart | status" >&2
     exit 1
     ;;
esac

exit $?
