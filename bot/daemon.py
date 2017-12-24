# -*- coding: utf-8 -*-

# Copyright (c) 2015  Sergey SoulBlader <dev@soulblader.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


import os
import sys
import signal

import logging
log = logging.getLogger(__name__)

DEFAULT_PID_DIR = os.path.abspath(os.path.dirname(__file__))


class Pid(object):

    def __init__(self, pidfile):
        """
        Object constructor expects the following arguments:

        :pidfile:  path to the pid file
        """
        self._pidfile = os.path.abspath(pidfile)

    def acquire(self):
        """ Write pid to pidfile """

        log.debug('pidfile -> %(path)s' % dict(path=self.filename))

        try:
            pid_fd = os.open(
                self.filename,
                os.O_CREAT|os.O_EXCL|os.O_WRONLY,
                0o644
            )

            pid = os.getpid()
            log.debug('pid -> %(pid)d' % dict(pid=pid))

            print(pid)
            os.write(pid_fd, str(pid).encode('utf-8'))
            os.close(pid_fd)
        except Exception as e:
            log.exception(e)

    def release(self):
        """ Remove pidfile """
        log.debug('removing pid lock file %(path)s...' % dict(path=self.filename))
        if self.is_locked():
            os.unlink(self.filename)
            log.debug('pid lock removed')
        else:
            log.debug('pid is not locked')

    def is_locked(self):
        """ Is pidfile exists """
        return os.path.isfile(self.filename)

    def is_running(self):
        if self.is_locked():
            try:
                os.kill(self.value, signal.SIG_DFL)
            except OSError:
                self.release()
            else:
                return True

    @property
    def filename(self):
        """ Pid filename """
        return self._pidfile

    @property
    def value(self):
        """ Pid value """
        try:
            with open(self.filename, 'rb') as fp:
                return int(fp.read().rstrip())
        except Exception as err:
            print(err)
            pass

    def __repr__(self):
        return '<%(name)s[%(value)s]>' % dict(
            name=type(self).__name__,
            value=self.value
        )


class Daemonize(object):
    """ Daemonize object """
    #TODO: change workdir
    def __init__(self, config, umask=0o22, workdir='/Users/skv/Documents/safeEat/bot/', stdin=os.devnull, stderr=os.devnull, stdout=os.devnull, keep_fds=None):
        """
        Object constructor expects the following arguments:

        :app:      contains the application name which will be sent to log
        :pid:      path to pid file
        :umask:    assign umask to process
        :workdir:  change dir to `workdir` before start
        :uid:      assign process to user id
        :gid:      assign process to group id id
        :stdin:    redirect stdin fo file
        :stderr:   redirect stderr fo file
        :stdout:   redirect stdout fo file
        :keep_fds: optional list of fds which should not be closed

        """

        self.umask = umask

        if keep_fds:
            self.keep_fds = set(keep_fds)
        else:
            self.keep_fds = set()

        self._workdir = workdir
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        # self._opened = False
        self._uid = config.uid or os.getuid()
        self._gid = config.gid or os.getgid()


        pid_dir = config.pid_dir

        if not pid_dir:
            pid_dir = DEFAULT_PID_DIR
        elif not os.path.isabs(pid_dir):
            pid_dir = os.path.join(
                os.path.dirname(config.config_filename),
                pid_dir
            )

        # Get pid filename from config object
        pid_name = config.pid_name

        if not pid_name:
            pid_name = '%(name)s.pid' % dict(name=__package__)

        pid = os.path.join(pid_dir, pid_name)

        if not os.path.isdir(pid_dir):
            try:
                os.mkdir(pid_dir, 0o755)
                log.debug('created directory -> %(path)s' % dict(path=pid_dir))
            except OSError:
                log.debug('directory %(path)s already exists' % dict(
                    path=pid_dir
                ))

        try:
            os.chown(pid_dir, self._uid, self._gid)
            log.debug('changed ownship for %(path)s to %(uid)d:%(gid)d' % dict(
                path=pid_dir,
                uid=self._uid,
                gid=self._gid
            ))
        except OSError:
            log.exception('failed to change ownship of %(path)s for %(uid)s:%(gid)s' % dict(
                path=pid_dir,
                uid=self._uid,
                gid=self._gid
            ))

        self.pid = Pid(pid)
        if self.pid.is_running():
            raise RuntimeError('process already running, pid: %(pid)d' % dict(
                pid=self.pid.value
            ))

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        self.pid.release()
        # self._opened = False

    def __enter__(self):

        piddir = os.path.dirname(self.pid.filename)

        if not os.path.isdir(piddir):
            try:
                os.mkdir(piddir, 0o755)
            except OSError:
                raise
        try:
            os.chown(piddir, self._uid, self._gid)
        except OSError:
            raise

        # First fork (detaches from parent)
        try:
            if os.fork() > 0:
                os._exit(0)
        except OSError as e:
            raise RuntimeError('fork #1 failed: %(e)' % vars())

        os.umask(self.umask)
        os.chdir(self._workdir)
        os.setgid(self._gid)
        os.setuid(self._uid)
        os.setsid()

        # Second fork (relinquish session leadership)
        try:
            if os.fork() > 0:
                os._exit(0)
        except OSError as e:
            raise RuntimeError('fork #2 failed: %(e)' % vars())

        sys.stdout.flush()
        sys.stderr.flush()

        with open(self._stdin, 'rb') as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open(self._stdout, 'ab') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
        with open(self._stderr, 'ab') as f:
            os.dup2(f.fileno(), sys.stderr.fileno())

        if self.pid:
            self.pid.acquire()

        # self._opened = True

        return self
