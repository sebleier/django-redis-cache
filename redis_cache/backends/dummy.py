from django.core.cache.backends.dummy import DummyCache


class RedisDummyCache(DummyCache):
    def ttl(self, key):
        return 0

    def delete_pattern(self, pattern, version=None):
        raise NotImplementedError

    def get_or_set(self, key, func, timeout=None):
        if not callable(func):
            raise Exception("Must pass in a callable")

        return func()

    def reinsert_keys(self):
        raise NotImplementedError

    def persist(self, key):
        return True

    def expire(self, key, timeout):
        return True
