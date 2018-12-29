import fnmatch
import re

from django.core.cache.backends.locmem import LocMemCache


class RedisLocMemCache(LocMemCache):
    def ttl(self, key):
        return 0

    def delete_pattern(self, pattern, version=None):
        pattern_key = self.make_key(pattern, version=version)
        self.validate_key(pattern_key)
        with self._lock:
            regex = fnmatch.translate(pattern_key)
            keys = [key for key in self._cache.keys() if re.match(regex, key)]
            for key in keys:
                self._delete(key)

    def get_or_set(self, key, func, timeout=None):
        if not callable(func):
            raise Exception("Must pass in a callable")

        return func()

    def reinsert_keys(self):
        return None

    def persist(self, key):
        return True

    def expire(self, key, timeout):
        return True
