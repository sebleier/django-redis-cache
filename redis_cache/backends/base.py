from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib
from django.utils.functional import cached_property
from django.utils.importlib import import_module

from redis_cache.compat import smart_bytes, DEFAULT_TIMEOUT

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import redis
except ImportError:
    raise InvalidCacheBackendError("Redis cache backend requires the 'redis-py' library")

from redis.connection import DefaultParser

from redis_cache.connection import pool
from redis_cache.utils import CacheKey


class BaseRedisCache(BaseCache):

    def __init__(self, server, params):
        """
        Connect to Redis, and set up cache backend.
        """
        super(BaseRedisCache, self).__init__(params)
        self.server = server
        self.params = params or {}
        self.options = params.get('OPTIONS', {})

    def __getstate__(self):
        return {'params': self.params, 'server': self.server}

    def __setstate__(self, state):
        self.__init__(**state)

    def create_client(self, server):
        kwargs = {
            'db': self.db,
            'password': self.password,
        }
        if '://' in server:
            client = redis.Redis.from_url(
                server,
                parser_class=self.parser_class,
                **kwargs
            )
            kwargs.update(
                client.connection_pool.connection_kwargs,
                unix_socket_path=client.connection_pool.connection_kwargs.get('path'),
            )
        else:
            unix_socket_path = None
            if ':' in server:
                host, port = server.rsplit(':', 1)
                try:
                    port = int(port)
                except (ValueError, TypeError):
                    raise ImproperlyConfigured("Port value must be an integer")
            else:
                host, port = None, None
                unix_socket_path = server

            kwargs.update(host=host, port=port, unix_socket_path=unix_socket_path)
            client = redis.Redis(**kwargs)

        kwargs.update(
            parser_class=self.parser_class,
            connection_pool_class=self.connection_pool_class,
            connection_pool_class_kwargs=self.connection_pool_class_kwargs,
        )

        connection_pool = pool.get_connection_pool(**kwargs)
        client.connection_pool = connection_pool
        return client

    @cached_property
    def db(self):
        _db = self.params.get('db', self.options.get('DB', 1))
        try:
            return int(_db)
        except (ValueError, TypeError):
            raise ImproperlyConfigured("db value must be an integer")

    @cached_property
    def password(self):
        return self.params.get('password', self.options.get('PASSWORD', None))

    @cached_property
    def parser_class(self):
        cls = self.options.get('PARSER_CLASS', None)
        if cls is None:
            return DefaultParser
        mod_path, cls_name = cls.rsplit('.', 1)
        try:
            mod = importlib.import_module(mod_path)
            parser_class = getattr(mod, cls_name)
        except AttributeError:
            raise ImproperlyConfigured("Could not find parser class '%s'" % parser_class)
        except ImportError, e:
            raise ImproperlyConfigured("Could not find module '%s'" % e)
        return parser_class

    @cached_property
    def pickle_version(self):
        """
        Get the pickle version from the settings and save it for future use
        """
        _pickle_version = self.options.get('PICKLE_VERSION', -1)
        try:
            return int(_pickle_version)
        except (ValueError, TypeError):
            raise ImproperlyConfigured("pickle version value must be an integer")

    @cached_property
    def connection_pool_class(self):
        pool_class = self.options.get('CONNECTION_POOL_CLASS', 'redis.ConnectionPool')
        module_name, class_name = pool_class.rsplit('.', 1)
        module = import_module(module_name)
        try:
            return getattr(module, class_name)
        except AttributeError:
            raise ImportError('cannot import name %s' % class_name)

    @cached_property
    def connection_pool_class_kwargs(self):
        return self.options.get('CONNECTION_POOL_CLASS_KWARGS', {})

    @cached_property
    def master_client(self):
        """
        Get the write server:port of the master cache
        """
        cache = self.options.get('MASTER_CACHE', None)
        if cache is None:
            self._master_client = None
        else:
            self._master_client = None
            try:
                host, port = cache.split(":")
            except ValueError:
                raise ImproperlyConfigured("MASTER_CACHE must be in the form <host>:<port>")
            for client in self.clients.itervalues():
                connection_kwargs = client.connection_pool.connection_kwargs
                if connection_kwargs['host'] == host and connection_kwargs['port'] == int(port):
                    return client
            if self._master_client is None:
                raise ImproperlyConfigured("%s is not in the list of available redis-server instances." % cache)

    def serialize(self, value):
        return pickle.dumps(value, self.pickle_version)

    def deserialize(self, value):
        """
        Unpickles the given value.
        """
        value = smart_bytes(value)
        return pickle.loads(value)

    def get_value(self, original):
        try:
            value = int(original)
        except (ValueError, TypeError):
            value = self.deserialize(original)
        return value

    def prep_value(self, value):
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return self.serialize(value)

    def make_key(self, key, version=None):
        if not isinstance(key, CacheKey):
            versioned_key = super(BaseRedisCache, self).make_key(key, version)
            return CacheKey(key, versioned_key)
        return key

    def make_keys(self, keys, version=None):
        return [self.make_key(key, version=version) for key in keys]

    ####################
    # Django cache api #
    ####################

    def _add(self, client, key, value, timeout):
        return self._set(key, value, timeout, client, _add_only=True)

    def add(self, key, value, timeout=None, version=None):
        """
        Add a value to the cache, failing if the key already exists.

        Returns ``True`` if the object was added, ``False`` if not.
        """
        raise NotImplementedError

    def _get(self, client, key, default=None):
        value = client.get(key)
        if value is None:
            return default
        value = self.get_value(value)
        return value

    def get(self, key, default=None, version=None):
        """
        Retrieve a value from the cache.

        Returns unpickled value if key is found, the default if not.
        """
        raise NotImplementedError

    def __set(self, client, key, value, timeout, _add_only=False):
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

    def _set(self, key, value, timeout=DEFAULT_TIMEOUT, client=None, _add_only=False):
        """
        Persist a value to the cache, and set an optional expiration time.
        """
        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout
        if timeout is not None:
            timeout = int(timeout)
        # If ``value`` is not an int, then pickle it
        if not isinstance(value, int) or isinstance(value, bool):
            result = self.__set(client, key, pickle.dumps(value), timeout, _add_only)
        else:
            result = self.__set(client, key, value, timeout, _add_only)
        # result is a boolean
        return result

    def set(self, key, value, timeout=None, version=None, client=None):
        """
        Persist a value to the cache, and set an optional expiration time.
        """
        raise NotImplementedError()

    def _delete(self, client, key):
        return client.delete(key)

    def delete(self, key, version=None):
        """
        Remove a key from the cache.
        """
        raise NotImplementedError

    def _delete_many(self, client, keys):
        return client.delete(*keys)

    def delete_many(self, keys, version=None):
        """
        Remove multiple keys at once.
        """
        raise NotImplementedError

    def _clear(self, client):
        return client.flushdb()

    def clear(self, version=None):
        """
        Flush cache keys.

        If version is specified, all keys belonging the version's key
        namespace will be deleted.  Otherwise, all keys will be deleted.
        """
        raise NotImplementedError

    def _get_many(self, client, original_keys, versioned_keys):
        """
        Retrieve many keys.
        """
        recovered_data = {}
        map_keys = dict(zip(versioned_keys, original_keys))

        results = client.mget(versioned_keys)

        for key, value in zip(versioned_keys, results):
            if value is None:
                continue
            recovered_data[map_keys[key]] = self.get_value(value)

        return recovered_data

    def get_many(self, keys, version=None):
        raise NotImplementedError

    def _set_many(self, client, data):
        new_data = {}
        for key, value in data.items():
            new_data[key] = self.prep_value(value)

        return client.mset(new_data)

    def set_many(self, data, timeout=None, version=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        raise NotImplementedError

    def _incr(self, client, key, delta=1):
        exists = client.exists(key)
        if not exists:
            raise ValueError("Key '%s' not found" % key)
        try:
            value = client.incr(key, delta)
        except redis.ResponseError:
            value = self._get(client, key) + delta
            self._set(client, key, value, timeout=None)
        return value

    def incr(self, key, delta=1, version=None):
        """
        Add delta to value in the cache. If the key does not exist, raise a
        ValueError exception.
        """
        raise NotImplementedError

    def _incr_version(self, client, old, new, delta, version):
        try:
            client.rename(old, new)
        except redis.ResponseError:
            raise ValueError("Key '%s' not found" % old._original_key)

        return version + delta

    def incr_version(self, key, delta=1, version=None):
        """
        Adds delta to the cache version for the supplied key. Returns the
        new version.

        """
        raise NotImplementedError

    #####################
    # Extra api methods #
    #####################

    def _has_key(self, client, key, version=None):
        """Returns True if the key is in the cache and has not expired."""
        key = self.make_key(key, version=version)
        return client.exists(key)

    def has_key(self, key, version=None):
        raise NotImplementedError

    def _ttl(self, client, key):
        """
        Returns the 'time-to-live' of a key.  If the key is not volitile, i.e.
        it has not set expiration, then the value returned is None.  Otherwise,
        the value is the number of seconds remaining.  If the key does not exist,
        0 is returned.
        """
        if client.exists(key):
            return client.ttl(key)
        return 0

    def ttl(self, key, version=None):
        raise NotImplementedError

    def _delete_pattern(self, client, pattern):
        keys = client.keys(pattern)
        if len(keys):
            client.delete(*keys)

    def delete_pattern(self, pattern, version=None):
        raise NotImplementedError

    def _get_or_set(self, client, key, func, timeout=None):
        if not callable(func):
            raise Exception("func must be a callable")

        dogpile_lock_key = "_lock" + key._versioned_key
        dogpile_lock = client.get(dogpile_lock_key)

        if dogpile_lock is None:
            self._set(dogpile_lock_key, 0, None, client)
            value = func()
            self.__set(client, key, self.prep_value(value), None)
            self.__set(client, dogpile_lock_key, 0, timeout)
        else:
            value = self._get(client, key)

        return value

    def get_or_set(self, key, func, timeout=None, version=None):
        raise NotImplementedError

    def _reinsert_keys(self, client):
        keys = client.keys('*')
        for key in keys:
            timeout = client.ttl(key)
            value = self.deserialize(client.get(key))

            if timeout is None:
                client.set(key, self.prep_value(value))

    def reinsert_keys(self):
        """
        Reinsert cache entries using the current pickle protocol version.
        """
        raise NotImplementedError
