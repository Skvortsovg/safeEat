# -*- coding: utf-8 -*-

import threading
from functools import wraps
import os
import signal
import errno


def async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
    return wrapper


class Callback(object):

    def __init__(self, func, *args, **kwargs):
        self.__call = func, args, kwargs

    def __call__(self):
        func, args, kwargs = self.__call
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()

    def __repr__(self):
        func, args, kwargs = self.__call
        pa = map(str, args)
        pa.extend(['='.join(map(str, k)) for k in kwargs.iteritems()])
        return '<%(name)s(%(func_name)s(%(args)s))>' % dict(
            name=type(self).__name__,
            func_name=func.func_name,
            args=', '.join(pa)
        )

class TimeoutError(Exception):
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator
