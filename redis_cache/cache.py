from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib
from django.utils.datastructures import SortedDict
from .compat import (smart_text, smart_bytes, bytes_type,
                     python_2_unicode_compatible, DEFAULT_TIMEOUT)

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import redis
except ImportError:
    raise InvalidCacheBackendError(
        "Redis cache backend requires the 'redis-py' library")
from redis.connection import UnixDomainSocketConnection, Connection
from redis.connection import DefaultParser


@python_2_unicode_compatible
class CacheKey(object):
    """
    A stub string class that we can use to check if a key was created already.
    """
    def __init__(self, key):
        self._key = key

    def __eq__(self, other):
        return self._key == other

    def __str__(self):
        return smart_text(self._key)

    def __repr__(self):
        return repr(self._key)

    def __hash__(self):
        return hash(self._key)


class CacheConnectionPool(object):

    def __init__(self):
        self._connection_pools = {}

    def get_connection_pool(self, host='127.0.0.1', port=6379, db=1,
                            password=None, parser_class=None,
                            unix_socket_path=None, connection_pool_class=None,
                            connection_pool_class_kwargs=None):
        connection_identifier = (host, port, db, parser_class, unix_socket_path, connection_pool_class)
        if not self._connection_pools.get(connection_identifier):
            connection_class = (
                unix_socket_path and UnixDomainSocketConnection or Connection
            )
            kwargs = {
                'db': db,
                'password': password,
                'connection_class': connection_class,
                'parser_class': parser_class,
            }
            kwargs.update(connection_pool_class_kwargs)
            if unix_socket_path is None:
                kwargs.update({
                    'host': host,
                    'port': port,
                })
            else:
                kwargs['path'] = unix_socket_path
            self._connection_pools[connection_identifier] = connection_pool_class(**kwargs)
        return self._connection_pools[connection_identifier]
pool = CacheConnectionPool()


class CacheClass(BaseCache):
    def __init__(self, server, params):
        """
        Connect to Redis, and set up cache backend.
        """
        self._init(server, params)

    def _init(self, server, params):
        super(CacheClass, self).__init__(params)
        self._server = server
        self._params = params

        unix_socket_path = None
        if ':' in self.server:
            host, port = self.server.rsplit(':', 1)
            try:
                port = int(port)
            except (ValueError, TypeError):
                raise ImproperlyConfigured("port value must be an integer")
        else:
            host, port = None, None
            unix_socket_path = self.server

        kwargs = {
            'db': self.db,
            'password': self.password,
            'host': host,
            'port': port,
            'unix_socket_path': unix_socket_path,
        }

        connection_pool = pool.get_connection_pool(
            parser_class=self.parser_class,
            connection_pool_class=self.connection_pool_class,
            connection_pool_class_kwargs=self.connection_pool_class_kwargs,
            **kwargs
        )
        self._client = redis.Redis(
            connection_pool=connection_pool,
            **kwargs
        )

    @property
    def server(self):
        return self._server or "127.0.0.1:6379"

    @property
    def params(self):
        return self._params or {}

    @property
    def options(self):
        return self.params.get('OPTIONS', {})

    @property
    def connection_pool_class(self):
        cls = self.options.get('CONNECTION_POOL_CLASS', 'redis.ConnectionPool')
        mod_path, cls_name = cls.rsplit('.', 1)
        try:
            mod = importlib.import_module(mod_path)
            pool_class = getattr(mod, cls_name)
        except (AttributeError, ImportError):
            raise ImproperlyConfigured("Could not find connection pool class '%s'" % cls)
        return pool_class

    @property
    def connection_pool_class_kwargs(self):
        return self.options.get('CONNECTION_POOL_CLASS_KWARGS', {})

    @property
    def db(self):
        _db = self.params.get('db', self.options.get('DB', 1))
        try:
            _db = int(_db)
        except (ValueError, TypeError):
            raise ImproperlyConfigured("db value must be an integer")
        return _db

    @property
    def password(self):
        return self.params.get('password', self.options.get('PASSWORD', None))

    @property
    def parser_class(self):
        cls = self.options.get('PARSER_CLASS', None)
        if cls is None:
            return DefaultParser
        mod_path, cls_name = cls.rsplit('.', 1)
        try:
            mod = importlib.import_module(mod_path)
            parser_class = getattr(mod, cls_name)
        except (AttributeError, ImportError):
            raise ImproperlyConfigured("Could not find parser class '%s'" % parser_class)
        return parser_class

    def __getstate__(self):
        return {'params': self._params, 'server': self._server}

    def __setstate__(self, state):
        self._init(**state)

    def make_key(self, key, version=None):
        """
        Returns the utf-8 encoded bytestring of the given key as a CacheKey
        instance to be able to check if it was "made" before.
        """
        if not isinstance(key, CacheKey):
            key = CacheKey(key)
        return key

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Add a value to the cache, failing if the key already exists.

        Returns ``True`` if the object was added, ``False`` if not.
        """
        return self.set(key, value, timeout, _add_only=True)

    def get(self, key, default=None, version=None):
        """
        Retrieve a value from the cache.

        Returns unpickled value if key is found, the default if not.
        """
        key = self.make_key(key, version=version)
        value = self._client.get(key)
        if value is None:
            return default
        try:
            result = int(value)
        except (ValueError, TypeError):
            result = self.unpickle(value)
        return result

    def _set(self, key, value, timeout, client, _add_only=False):
        if timeout is None or timeout == 0:
            if _add_only:
                return client.setnx(key, value)
            return client.set(key, value)
        elif timeout > 0:
            if _add_only:
                added = client.setnx(key, value)
                if added:
                    client.expire(key, timeout)
                return added
            return client.setex(key, value, timeout)
        else:
            return False

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, client=None, _add_only=False):
        """
        Persist a value to the cache, and set an optional expiration time.
        """
        if not client:
            client = self._client
        key = self.make_key(key, version=version)
        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout
        if timeout is not None:
            timeout = int(timeout)

        # If ``value`` is not an int, then pickle it
        if not isinstance(value, int) or isinstance(value, bool):
            result = self._set(key, pickle.dumps(value), timeout, client, _add_only)
        else:
            result = self._set(key, value, timeout, client, _add_only)
        # result is a boolean
        return result

    def delete(self, key, version=None):
        """
        Remove a key from the cache.
        """
        self._client.delete(self.make_key(key, version=version))

    def delete_many(self, keys, version=None):
        """
        Remove multiple keys at once.
        """
        if keys:
            keys = map(lambda key: self.make_key(key, version=version), keys)
            self._client.delete(*keys)

    def clear(self):
        """
        Flush all cache keys.
        """
        # TODO : potential data loss here, should we only delete keys based on the correct version ?
        self._client.flushdb()

    def unpickle(self, value):
        """
        Unpickles the given value.
        """
        value = smart_bytes(value)
        return pickle.loads(value)

    def get_many(self, keys, version=None):
        """
        Retrieve many keys.
        """
        if not keys:
            return {}
        recovered_data = SortedDict()
        new_keys = list(map(lambda key: self.make_key(key, version=version), keys))
        map_keys = dict(zip(new_keys, keys))
        results = self._client.mget(new_keys)
        for key, value in zip(new_keys, results):
            if value is None:
                continue
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = self.unpickle(value)
            if isinstance(value, bytes_type):
                value = smart_text(value)
            recovered_data[map_keys[key]] = value
        return recovered_data

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        pipeline = self._client.pipeline()
        for key, value in data.items():
            self.set(key, value, timeout, version=version, client=pipeline)
        pipeline.execute()

    def incr(self, key, delta=1, version=None):
        """
        Add delta to value in the cache. If the key does not exist, raise a
        ValueError exception.
        """
        key = self.make_key(key, version=version)
        exists = self._client.exists(key)
        if not exists:
            raise ValueError("Key '%s' not found" % key)
        try:
            value = self._client.incr(key, delta)
        except redis.ResponseError:
            value = self.get(key) + delta
            self.set(key, value)
        return value

    def ttl(self, key, version=None):
        """
        Returns the 'time-to-live' of a key.  If the key is not volitile, i.e.
        it has not set expiration, then the value returned is None.  Otherwise,
        the value is the number of seconds remaining.  If the key does not exist,
        0 is returned.
        """
        key = self.make_key(key, version=version)
        if self._client.exists(key):
            return self._client.ttl(key)
        return 0

    def has_key(self, key, version=None):
        """
        Returns True if the key is in the cache and has not expired.
        """
        key = self.make_key(key, version=version)
        return self._client.exists(key)


class RedisCache(CacheClass):
    """
    A subclass that is supposed to be used on Django >= 1.3.
    """

    def make_key(self, key, version=None):
        if not isinstance(key, CacheKey):
            key = CacheKey(super(CacheClass, self).make_key(key, version))
        return key

    def incr_version(self, key, delta=1, version=None):
        """
        Adds delta to the cache version for the supplied key. Returns the
        new version.

        Note: In Redis 2.0 you cannot rename a volitile key, so we have to move
        the value from the old key to the new key and maintain the ttl.
        """
        if version is None:
            version = self.version
        old_key = self.make_key(key, version)
        value = self.get(old_key, version=version)
        ttl = self._client.ttl(old_key)
        if value is None:
            raise ValueError("Key '%s' not found" % key)
        new_key = self.make_key(key, version=version + delta)
        # TODO: See if we can check the version of Redis, since 2.2 will be able
        # to rename volitile keys.
        self.set(new_key, value, timeout=ttl)
        self.delete(old_key)
        return version + delta

