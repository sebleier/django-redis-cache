try:
    import cPickle as pickle
except ImportError:
    import pickle
import random

from django.core.cache.backends.base import DEFAULT_TIMEOUT

from redis_cache.backends.base import BaseRedisCache


class RedisCache(BaseRedisCache):

    def __init__(self, server, params):
        """
        Connect to Redis, and set up cache backend.
        """
        super(RedisCache, self).__init__(server, params)

        for server in self.servers:
            client = self.create_client(server)
            self.clients[client.connection_pool.connection_identifier] = client

        self.client_list = self.clients.values()
        self.master_client = self.get_master_client()
        self.ro_slaves_list = []
        if self.options.get('MASTER_CACHE_ONLY_FOR_WRITE', False):
            for identifier, client in self.clients.items():
                if identifier != self.master_client.connection_pool.connection_identifier:  # noqa: E501
                    self.ro_slaves_list.append(client)

    def get_client(self, key, write=False):
        if write and self.master_client is not None:
            return self.master_client
        if self.ro_slaves_list:
            return random.choice(self.ro_slaves_list)
        return random.choice(list(self.client_list))

    ####################
    # Django cache api #
    ####################

    def delete_many(self, keys, version=None):
        """Remove multiple keys at once."""
        versioned_keys = self.make_keys(keys, version=version)
        if versioned_keys:
            self._delete_many(self.master_client, versioned_keys)

    def clear(self, version=None):
        """Flush cache keys.

        If version is specified, all keys belonging the version's key
        namespace will be deleted.  Otherwise, all keys will be deleted.
        """
        if version is None:
            self._clear(self.master_client)
        else:
            self.delete_pattern('*', version=version)

    def get_many(self, keys, version=None):
        versioned_keys = self.make_keys(keys, version=version)
        return self._get_many(self.master_client, keys, versioned_keys=versioned_keys)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        timeout = self.get_timeout(timeout)

        versioned_keys = self.make_keys(data.keys(), version=version)
        if timeout is None:
            new_data = {}
            for key in versioned_keys:
                new_data[key] = self.prep_value(data[key._original_key])
            return self._set_many(self.master_client, new_data)

        pipeline = self.master_client.pipeline()
        for key in versioned_keys:
            value = self.prep_value(data[key._original_key])
            self._set(pipeline, key, value, timeout)
        pipeline.execute()

    def incr_version(self, key, delta=1, version=None):
        """
        Adds delta to the cache version for the supplied key. Returns the
        new version.

        """
        if version is None:
            version = self.version

        old = self.make_key(key, version)
        new = self.make_key(key, version=version + delta)

        return self._incr_version(self.master_client, old, new, delta, version)

    #####################
    # Extra api methods #
    #####################

    def delete_pattern(self, pattern, version=None):
        pattern = self.make_key(pattern, version=version)
        self._delete_pattern(self.master_client, pattern)

    def reinsert_keys(self):
        """
        Reinsert cache entries using the current pickle protocol version.
        """
        self._reinsert_keys(self.master_client)
