from collections import defaultdict

from django.core.cache.backends.base import DEFAULT_TIMEOUT

from redis_cache.backends.base import BaseRedisCache
from redis_cache.sharder import HashRing


class ShardedRedisCache(BaseRedisCache):

    def __init__(self, server, params):
        super(ShardedRedisCache, self).__init__(server, params)
        self.sharder = HashRing()

        for server in self.servers:
            client = self.create_client(server)
            self.clients[client.connection_pool.connection_identifier] = client
            self.sharder.add(client.connection_pool.connection_identifier)

        self.client_list = self.clients.values()

    def get_client(self, key, write=False):
        node = self.sharder.get_node(key)
        return self.clients[node]

    def shard(self, keys, write=False, version=None):
        """
        Returns a dict of keys that belong to a cache's keyspace.
        """
        clients = defaultdict(list)
        for key in keys:
            clients[self.get_client(key, write)].append(
                self.make_key(key, version)
            )
        return clients

    ####################
    # Django cache api #
    ####################

    def delete_many(self, keys, version=None):
        """
        Remove multiple keys at once.
        """
        clients = self.shard(keys, write=True, version=version)
        for client, keys in clients.items():
            self._delete_many(client, keys)

    def clear(self, version=None):
        """
        Flush cache keys.

        If version is specified, all keys belonging the version's key
        namespace will be deleted.  Otherwise, all keys will be deleted.
        """
        if version is None:
            for client in self.clients.values():
                self._clear(client)
        else:
            self.delete_pattern('*', version=version)

    def get_many(self, keys, version=None):
        data = {}
        clients = self.shard(keys, version=version)
        for client, versioned_keys in clients.items():
            original_keys = [key._original_key for key in versioned_keys]
            data.update(
                self._get_many(
                    client,
                    original_keys,
                    versioned_keys=versioned_keys
                )
            )
        return data

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        timeout = self.get_timeout(timeout)

        clients = self.shard(data.keys(), write=True, version=version)

        if timeout is None:
            for client, keys in clients.items():
                subset = {}
                for key in keys:
                    subset[key] = self.prep_value(data[key._original_key])
                self._set_many(client, subset)
            return

        for client, keys in clients.items():
            pipeline = client.pipeline()
            for key in keys:
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

        client = self.get_client(key, write=True)
        old = self.make_key(key, version=version)
        new = self.make_key(key, version=version + delta)

        return self._incr_version(client, old, new, delta, version)

    #####################
    # Extra api methods #
    #####################

    def delete_pattern(self, pattern, version=None):
        pattern = self.make_key(pattern, version=version)
        for client in self.clients.values():
            self._delete_pattern(client, pattern)

    def get_pattern(self, pattern, version=None):
        pattern = self.make_key(pattern, version=version)
        recovered_data = {}
        for client in self.clients.values():
            recovered_data.update(self._get_pattern(client, pattern))
        return recovered_data if recovered_data else None

    def reinsert_keys(self):
        """
        Reinsert cache entries using the current pickle protocol version.
        """
        for client in self.clients.values():
            self._reinsert_keys(client)
