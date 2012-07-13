import sys
from collections import defaultdict
from math import ceil
from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib
from django.utils.encoding import smart_unicode, smart_str
from django.utils.datastructures import SortedDict

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
from redis_cache.sharder import CacheSharder


class CacheKey(object):
    """
    A stub string class that we can use to check if a key was created already.
    """
    def __init__(self, key):
        self._key = key

    def __eq__(self, other):
        return self._key == other

    def __unicode__(self):
        return smart_str(self._key)

    __repr__ = __str__ = __unicode__


class CacheConnectionPool(object):

    def __init__(self):
        self._connection_pools = {}

    def get_connection_pool(self, host='127.0.0.1', port=6379, db=1,
                            password=None, parser_class=None,
                            unix_socket_path=None):
        connection_identifier = (host, port, db, parser_class, unix_socket_path)
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
            if unix_socket_path is None:
                kwargs.update({
                    'host': host,
                    'port': port,
                })
            else:
                kwargs['path'] = unix_socket_path
            self._connection_pools[connection_identifier] = redis.ConnectionPool(**kwargs)
        return self._connection_pools[connection_identifier]
pool = CacheConnectionPool()


class RedisCache(BaseCache):

    def __init__(self, server, params):
        """
        Connect to Redis, and set up cache backend.
        """
        self._init(server, params)

    def _init(self, server, params):
        super(RedisCache, self).__init__(params)
        self._params = params
        self._server = server
        self._pickle_version = None
        self.__master_client = None
        self.clients = []
        self.sharder = CacheSharder()

        if not isinstance(server, (list, tuple)):
            servers = [server]
        else:
            servers = server

        for server in servers:
            unix_socket_path = None
            if ':' in server:
                host, port = server.rsplit(':', 1)
                try:
                    port = int(port)
                except (ValueError, TypeError):
                    raise ImproperlyConfigured("port value must be an integer")
            else:
                host, port = None, None
                unix_socket_path = server

            kwargs = {
                'db': self.db,
                'password': self.password,
                'host': host,
                'port': port,
                'unix_socket_path': unix_socket_path,
            }
            connection_pool = pool.get_connection_pool(
                parser_class=self.parser_class,
                **kwargs
            )
            client = redis.Redis(
                connection_pool=connection_pool,
                **kwargs
            )
            self.clients.append(client)
            self.sharder.add(client, "%s:%s" % (host, port))

    @property
    def params(self):
        return self._params or {}

    @property
    def options(self):
        return self.params.get('OPTIONS', {})

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
        except AttributeError:
            raise ImproperlyConfigured("Could not find parser class '%s'" % parser_class)
        except ImportError, e:
            raise ImproperlyConfigured("Could not find module '%s'" % e)
        return parser_class

    @property
    def pickle_version(self):
        """
        Get the pickle version from the settings and save it for future use
        """
        if self._pickle_version is None:
            _pickle_version = self.options.get('PICKLE_VERSION', -1)
            try:
                _pickle_version = int(_pickle_version)
            except (ValueError, TypeError):
                raise ImproperlyConfigured("pickle version value must be an integer")
            self._pickle_version = _pickle_version
        return self._pickle_version

    @property
    def master_client(self):
        """
        Get the write server:port of the master cache
        """
        if not hasattr(self, '_master_client') and self.__master_client is None:
            cache = self.options.get('MASTER_CACHE', None)
            if cache is None:
                self._master_client = None
            else:
                self._master_client = None
                try:
                    host, port = cache.split(":")
                except ValueError:
                    raise ImproperlyConfigured("MASTER_CACHE must be in the form <host>:<port>")
                for client in self.clients:
                    connection_kwargs = client.connection_pool.connection_kwargs
                    if connection_kwargs['host'] == host and connection_kwargs['port'] == int(port):
                        self._master_client = client
                        break
                if self._master_client is None:
                    raise ImproperlyConfigured("%s is not in the list of available redis-server instances." % cache)
        return self._master_client

    def __getstate__(self):
        return {'params': self._params, 'server': self._server}

    def __setstate__(self, state):
        self._init(**state)

    def serialize(self, value):
        return pickle.dumps(value, self.pickle_version)

    def deserialize(self, value):
        """
        Unpickles the given value.
        """
        return pickle.loads(value)

    def get_value(self, original):
        try:
            value = int(original)
        except (ValueError, TypeError):
            value = self.deserialize(original)
        return value

    def get_client(self, key, for_write=False):
        if for_write and self.master_client is not None:
            return self.master_client
        return self.sharder.get_client(key)

    def shard(self, keys, for_write=False, version=None):
        """
        Returns a dict of keys that belong to a cache's keyspace.
        """
        clients = defaultdict(list)
        for key in keys:
            clients[self.get_client(key, for_write)].append(key)
        return clients

    def make_key(self, key, version=None):
        if not isinstance(key, CacheKey):
            key = super(RedisCache, self).make_key(key, version)
            key = CacheKey(key)
        return key

    ####################
    # Django cache api #
    ####################

    def add(self, key, value, timeout=None, version=None):
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
        client = self.get_client(key)
        key = self.make_key(key, version=version)
        value = client.get(key)
        if value is None:
            return default
        value = self.get_value(value)
        return value

    def _set(self, key, value, timeout, client, _add_only=False):
        if timeout == 0:
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

    def set(self, key, value, timeout=None, version=None, client=None, _add_only=False):
        """
        Persist a value to the cache, and set an optional expiration time.
        """
        if client is None:
            client = self.get_client(key, for_write=True)
        key = self.make_key(key, version=version)
        if timeout is None:
            timeout = self.default_timeout
        try:
            value = float(value)
            # If you lose precision from the typecast to str, then pickle value
            if int(value) != value:
                raise TypeError
        except (ValueError, TypeError):
            result = self._set(key, self.serialize(value), int(timeout), client, _add_only)
        else:
            result = self._set(key, int(value), int(timeout), client, _add_only)
        # result is a boolean
        return result

    def delete(self, key, version=None):
        """
        Remove a key from the cache.
        """
        client = self.get_client(key, for_write=True)
        key = self.make_key(key, version=version)
        client.delete(key)

    def delete_many(self, keys, version=None):
        """
        Remove multiple keys at once.
        """
        clients = self.shard(keys, for_write=True)
        for client, keys in clients.items():
            keys = [self.make_key(key, version=version) for key in keys]
            client.delete(*keys)

    def clear(self, version=None):
        """
        Flush cache keys.

        If version is specified, all keys belonging the version's key
        namespace will be deleted.  Otherwise, all keys will be deleted.
        """
        if version is None:
            if self.master_client is None:
                for client in self.clients:
                    client.flushdb()
            else:
                self.master_client.flushdb()
        else:
            self.delete_pattern('*', version=version)

    def _get_many(self, client, keys, version=None):
        """
        Retrieve many keys.
        """
        if not keys:
            return {}
        recovered_data = SortedDict()
        new_keys = map(lambda key: self.make_key(key, version=version), keys)
        map_keys = dict(zip(new_keys, keys))
        results = client.mget(new_keys)
        for key, value in zip(new_keys, results):
            if value is None:
                continue
            value = self.get_value(value)
            recovered_data[map_keys[key]] = value
        return recovered_data

    def get_many(self, keys, version=None):
        data = {}
        clients = self.shard(keys)
        for client, keys in clients.items():
            data.update(self._get_many(client, keys, version=version))
        return data

    def set_many(self, data, timeout=None, version=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        clients = self.shard(data.keys(), for_write=True)
        for client, keys in clients.iteritems():
            pipeline = client.pipeline()
            for key in keys:
                self.set(key, data[key], timeout, version=version, client=pipeline)
            pipeline.execute()

    def incr(self, key, delta=1, version=None):
        """
        Add delta to value in the cache. If the key does not exist, raise a
        ValueError exception.
        """
        client = self.get_client(key, for_write=True)
        key = self.make_key(key, version=version)
        exists = client.exists(key)
        if not exists:
            raise ValueError("Key '%s' not found" % key)
        try:
            value = client.incr(key, delta)
        except redis.ResponseError:
            value = self.get(key) + 1
            self.set(key, value)
        return value

    def incr_version(self, key, delta=1, version=None):
        """
        Adds delta to the cache version for the supplied key. Returns the
        new version.

        """
        if version is None:
            version = self.version
        client = self.get_client(key, for_write=True)
        old = self.make_key(key, version)
        new = self.make_key(key, version=version + delta)
        try:
            client.rename(old, new)
        except redis.ResponseError:
            raise ValueError("Key '%s' not found" % key)

        return version + delta

    #####################
    # Extra api methods #
    #####################

    def delete_pattern(self, pattern, version=None):
        pattern = self.make_key(pattern, version=version)
        if self.master_client is None:
            for client in self.clients:
                keys = client.keys(pattern)
                if len(keys):
                    client.delete(*keys)
        else:
            keys = self.master_client.keys(pattern)
            if len(keys):
                self.master_client.delete(*keys)

    def reinsert_keys(self):
        """
        Reinsert cache entries using the current pickle protocol version.
        """
        def print_progress(i, progress):
            """
            Helper function to print out the progress of the reinsertion.
            """
            sys.stdout.flush()
            progress = int(ceil(progress * 80))
            msg = "Server %d / %d: |%s|\r" % (i + 1, len(self.clients), progress * "=" + (80 - progress) * " ")
            sys.stdout.write(msg)

        for i, client in enumerate(self.clients):
            keys = client.keys('*')
            for j, key in enumerate(keys):
                timeout = client.ttl(key)
                value = self.deserialize(client.get(key))
                if timeout is None:
                    timeout = 0
                try:
                    value = float(value)
                    # If you lose precision from the typecast to str, then pickle value
                    if int(value) != value:
                        raise TypeError
                except (ValueError, TypeError):
                    self._set(key, self.serialize(value), int(timeout), client)
                else:
                    self._set(key, int(value), int(timeout), client)
                progress = float(j) / len(keys)
                print_progress(i, progress)
        print_progress(i, 1)
        print
