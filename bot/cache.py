# -*- coding: utf-8 -*-

import redis
from functools import wraps
import time
from datetime import datetime, timedelta
from settings import REDIS_URL
try:
    import cPickle as pickle
except ImportError:
    import pickle

import logging
log = logging.getLogger(__name__)


class Error(Exception):
    pass


class RedisCacheError(Error):
    pass


class StrictRedis(redis.StrictRedis):

    def __init__(self, *args, **kwargs):
        super(StrictRedis, self).__init__(*args, **kwargs)
        self.set_response_callback('GET', lambda o: self.loads_obj(o) if o else None)
        self.set_response_callback('HGET', lambda o: self.loads_obj(o) if o else None)

    @staticmethod
    def loads_obj(obj):
        try:
            c = pickle.loads(obj)
        except pickle.UnpicklingError:
            c = obj
        return c

    def set(self, key, value, *args, **kwargs):
        pickled = kwargs.get('pickled', True)
        pvalue = pickle.dumps(value, pickle.HIGHEST_PROTOCOL) if pickled is True else value
        super(StrictRedis, self).set(key, pvalue, *args, **kwargs)

    def hset(self, key, name, value, *args, **kwargs):
        pickled = kwargs.get('pickled', True)
        pvalue = pickle.dumps(value, pickle.HIGHEST_PROTOCOL) if pickled is True else value
        super(StrictRedis, self).hset(key, name, pvalue, *args, **kwargs)


class RedisConnection(object):
    _connection_pool = None

    @classmethod
    def connectpool(cls, url):
        log.debug('Connection to redis: %(url)s' % vars())
        if cls._connection_pool is None:
            cls._connection_pool = redis.ConnectionPool().from_url(url)

    def get_connection(self):
        assert self._connection_pool is not None, 'pool is not connected'
        return StrictRedis(connection_pool=self._connection_pool)


class RedisCache(RedisConnection):

    def __init__(self, prefix='cached', **kwargs):
        self._key_prefix = prefix
        self._redis = self.get_connection()

    def ping(self):
        return self._redis.ping()

    def keys(self):
        return self._redis.keys(':'.join((self._key_prefix, '*')))

    def clear(self):
        with self._redis.pipeline() as pipe:
            map(pipe.delete, self.keys())
            n = sum(pipe.execute())
        return n

    def _delete(self, key):
        self._redis.delete(key)

    def _get(self, key):
        return self._redis.get(key)

    def _set(self, key, value=None, timeout=None):
        with self._redis.pipeline() as pipe:
            if value is not None:
                pipe.set(key, pickle.dumps(value, pickle.HIGHEST_PROTOCOL))

            if timeout is not None:
                if callable(timeout):
                    timeout = timeout()
                if isinstance(timeout, datetime):
                    pipe.expireat(key, timeout)
                elif isinstance(timeout, (int, float, timedelta,)):
                    pipe.expire(key, timeout)
                else:
                    raise RedisCacheError(
                        'unexpected timeout: %(timeout)r' % dict(
                            timeout=timeout
                        )
                    )

            else:
                ttl = self._ttl(key)
                if ttl > 0:
                    pipe.expire(key, ttl)

            pipe.execute()

    def _expire(self, key, timeout=None):

        if timeout is None:
            return
        elif callable(timeout):
            timeout = timeout()

        if isinstance(timeout, datetime):
            self._redis.expireat(key, timeout)
        elif isinstance(timeout, (int, float, timedelta,)) and timeout:
            self._redis.expire(key, timeout)
        else:
            raise RedisCacheError(
                'unexpected timeout: %(timeout)r' % dict(
                    timeout=timeout
                )
            )

    def _has(self, key):
        return self._redis.exists(key)

    def _ttl(self, key):
        return self._redis.ttl(key)


class SignatureCache(RedisCache):

    def getkey(self, obj):
        return ':'.join((self._key_prefix, str(hash(obj))))

    def delete(self, key):
        k = self.getkey(key)
        self._delete(k)
        return k

    def set(self, key, value=None, timeout=None):
        k = self.getkey(key)
        self._set(k, value=value, timeout=timeout)
        return k

    def get(self, key):
        k = self.getkey(key)
        return self._get(k)

    def expire(self, key, timeout=None):
        k = self.getkey(key)
        self._expire(k, timeout=timeout)

    def has(self, key):
        k = self.getkey(key)
        return self._has(k)

    def ttl(self, key):
        k = self.getkey(key)
        return self._ttl(k)


def cached(timeout=None):

    cache = SignatureCache(prefix='dc')

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            res = cache.get((func.func_name, args))
            if res is None:
                res = func(*args, **kwargs)
                assert isinstance(timeout, (int, timedelta, type(None))), (
                    'timeout must be `int`, `long` or `None` type'
                )
                cache.set((func.func_name, args), value=res, timeout=timeout)
            return res

        return wrapper

    return decorator


class AllowedPhoneList(RedisCache):

    def __init__(self, prefix='apl', **kwargs):
        super(AllowedPhoneList, self).__init__(prefix=prefix, kwargs=kwargs)

    def add(self, phone):
        return self._redis.sadd(self._key_prefix, phone)

    def remove(self, phone):
        return self._redis.srem(self._key_prefix, phone)

    def check(self, phone):
        return self._redis.sismember(self._key_prefix, phone)

    def list(self):
        return self._redis.smembers(self._key_prefix)

    def clear(self):
        self._redis.delete(self._key_prefix)

    def __contains__(self, phone):
        return self.check(phone)


class BaseContext(RedisCache):

    def __init__(self, chat_id, persist_prefix, tmp_prefix, **kwargs):
        super(BaseContext, self).__init__(kwargs=kwargs)
        self._key_p = ':'.join([persist_prefix, str(chat_id)])
        self._key_t = ':'.join([tmp_prefix, str(chat_id)])
        self._pipeline = None

    def key(self, persistent=True):
        return self._key_p if persistent is True else self._key_t

    @property
    def pipeline(self):
        if self._pipeline is None:
            self._pipeline = self._redis.pipeline()
        return self._pipeline

    def apply(self):
        res = self.pipeline.execute()
        self._pipeline = None
        return res

    # def _set_value_p(self, name, value, timeout=None, pickled=True):
    #     pvalue = pickle.dumps(value) if pickled is True else value
    #     self.pipeline.hset(self.key, name, pvalue)
    #     self._expire(timeout=timeout)

    def _expire(self, timeout=None, persistent=True):
        if timeout is not None:
            if callable(timeout):
                timeout = timeout()
            if isinstance(timeout, datetime):
                self.pipeline.expireat(self.key(persistent), timeout)
            elif isinstance(timeout, (int, float, timedelta,)):
                self.pipeline.expire(self.key(persistent), timeout)

    def set_(self, key, value, persistent=True):
        self._redis.hset(self.key(persistent), key, value)

    def get_(self, key, persistent=True):
        return self._redis.hget(self.key(persistent), key)

    def p_set_(self, key, value, timeout=None, pickled=True, persistent=True):
        pvalue = pickle.dumps(value) if pickled is True else value
        self.pipeline.hset(self.key(persistent), key, pvalue)
        self._expire(timeout=timeout, persistent=persistent)

    def p_get_(self, key, persistent=True):
        self.pipeline.hget(self.key(persistent), key)


class Context(BaseContext):

    def __init__(self, chat_id, persist_prefix='ucp', tmp_prefix='uct'):
        super(Context, self).__init__(chat_id, persist_prefix, tmp_prefix)

    def get_auth_n(self):
        return self._redis.hincrby(self.key(True), 'auth_n', 0)

    def p_get_auth_n(self):
        return self.pipeline.hincrby(self.key(True), 'auth_n', 0)

    def set_auth_n(self, n):
        self.set_('auth_n', n)

    def p_set_auth_n(self, n):
        self.p_set_('auth_n', n, pickled=False)

    def decr_auth_n(self):
        return self._redis.hincrby(self.key(True), 'auth_n', -1)

    def p_decr_auth_n(self):
        self.pipeline.hincrby(self.key(True), 'auth_n', -1)

    def incr_auth_n(self):
        return self._redis.hincrby(self.key(True), 'auth_n', 1)

    def p_incr_auth_n(self):
        self.pipeline.hincrby(self.key(True), 'auth_n', 1)


    def get_phone(self):
        return self.get_('phone')

    def p_get_phone(self):
        self.p_get_('phone')

    def set_phone(self, n):
        self.set_('phone', n)

    def p_set_phone(self, n):
        self.p_set_('phone', n)

    def get_lang(self):
        return self.get_('lang')

    def p_get_lang(self):
        self.p_get_('lang')

    def set_lang(self, n):
        self.set_('lang', n)

    def p_set_lang(self, n):
        self.p_set_('lang', n)

    def get_timezone(self):
        return self.get_('TZ')

    def p_get_timezone(self):
        self.p_get_('TZ')

    def set_timezone(self, n):
        self.set_('TZ', n)

    def p_set_timezone(self, n):
        self.p_set_('TZ', n)

    def get_username(self):
        return self.get_('username')

    def p_get_username(self):
        self.p_get_('username')

    def set_username(self, n):
        self.set_('username', n)

    def p_set_username(self, n):
        self.p_set_('username', n)

    def p_set_weight(self, n):
        self.p_set_('weight', n)

    def p_get_weight(self):
        self.p_get_('weight')

    def p_set_height(self, n):
        self.p_set_('height', n)

    def p_get_height(self):
        self.p_get_('height')

    def p_set_sex(self, n):
        self.p_set_('sex', n)

    def p_get_sex(self):
        self.p_get_('sex')

    def p_set_birth_year(self, n):
        self.p_set_('birth_year', n)

    def p_get_birth_year(self):
        self.p_get_('birth_year')

    def get_userid(self):
        return self.get_('userid')

    def p_get_userid(self):
        self.p_get_('userid')

    def set_userid(self, n):
        self.set_('userid', n)

    def p_set_userid(self, n):
        self.p_set_('userid', n)

    def get_authorized(self):
        return self.get_('authorized', persistent=False)

    def p_get_authorized(self):
        self.p_get_('authorized', persistent=False)

    def set_authorized(self):
        self.set_('authorized', True, persistent=False)

    def p_set_authorized(self, timeout=None):
        self.p_set_('authorized', True, timeout=timeout, persistent=False)

    def set_unauthorized(self):
        self.set_('authorized', False, persistent=False)

    def p_set_unauthorized(self):
        self.p_set_('authorized', False, persistent=False)

    def get_state(self):
        return self.get_('state', persistent=False)

    def p_get_state(self):
        self.p_get_('state', persistent=False)

    def set_state(self, n):
        # self.set_('state', n, persistent=False)
        self.p_set_state(self, n)
        self.apply()

    def p_set_state(self, n, timeout=None):
        self.p_set_('state', n, timeout=timeout, persistent=False)
        self.p_set_('last_seen', datetime.utcnow())

    def p_set_last_seen(self):
        self.p_set_('last_seen', datetime.utcnow())

    def get_last_seen(self):
        return self.get_('last_seen')

    def p_get_last_seen(self):
        self.p_get_('last_seen')

    def p_set_lifestyle(self, n):
        self.p_set_('lifestyle', n)

    def p_get_lifestyle(self):
        self.p_get_('lifestyle')

    def p_set_goal(self, n):
        self.p_set_('goal', n)

    def p_get_goal(self):
        self.p_get_('goal')

    def p_set_dish_title(self, n):
        self.p_set_('dish_title', n)

    def p_get_dish_title(self):
        self.p_get_('dish_title')

    def p_set_ingr_type(self, n):
        self.p_set_('ingr_type', n)

    def p_get_ingr_type(self):
        self.p_get_('ingr_type')


    def incr_requests_n(self):
        return self._redis.hincrby(self.key(True), 'req_n', 1)

    def p_incr_requests_n(self):
        self.pipeline.hincrby(self.key(True), 'req_n', 1)

    def get_requests_n(self):
        return self._redis.hincrby(self.key(True), 'req_n', 0)

    def p_get_requests_n(self):
        self.pipeline.hincrby(self.key(True), 'req_n', 0)


    def p_set_callback_func_args(self, args):
        self.p_set_('callback_func_args', args, persistent=False)

    def get_callback_func_args(self):
        self.p_get_('callback_func_args', persistent=False)

    def p_set_last_inline_keyboard_msg_id(self, msg_id):
        self.p_set_('last_inline_msg', msg_id, persistent=False)

    def get_last_inline_keyboard_msg_id(self):
        self.p_get_('last_inline_msg', persistent=False)

    def get_msg_id_to_remove_keyboard(self):
        self.p_get_('msg_id_to_remove_keyboard', persistent=False)



class BaseCacheData(RedisCache):

    def __init__(self, prefix, **kwargs):
        super(BaseCacheData, self).__init__(kwargs=kwargs)
        self._prefix = prefix
        self._pipeline = None

    def key(self):
            return self._prefix

    @property
    def pipeline(self):
        if self._pipeline is None:
            self._pipeline = self._redis.pipeline()
        return self._pipeline

    def apply(self):
        res = self.pipeline.execute()
        self._pipeline = None
        return res

    def _expire(self, timeout=None, persistent=True):
        if timeout is not None:
            if callable(timeout):
                timeout = timeout()
            if isinstance(timeout, datetime):
                self.pipeline.expireat(self.key(), timeout)
            elif isinstance(timeout, (int, float, timedelta,)):
                self.pipeline.expire(self.key(), timeout)

    # def set__(self, key, value, timeout=None):
    #     self.pipeline.hset(self.key(), key, value)
    #     self._expire(timeout=timeout)
    #
    # def get__(self, key):
    #     self.pipeline.hget(self.key(), key)

    def set_(self, key, value, timeout=None, pickled=True):
        pvalue = pickle.dumps(value) if pickled is True else value
        self.pipeline.hset(self.key(), key, pvalue)
        self._expire(timeout=timeout)

    def get_(self, key):
        self.pipeline.hget(self.key(), key)


RedisConnection.connectpool(REDIS_URL)
