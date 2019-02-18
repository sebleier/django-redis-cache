API Usage
*********

Standard Django Cache API
-------------------------

.. function:: get(self, key[, default=None]):

    Retrieves a value from the cache.

    :param key: Location of the value
    :param default: Value to return if key does not exist in cache.
    :rtype: Value that was cached.


.. function:: add(self, key, value[, timeout=DEFAULT_TIMEOUT]):

   Add a value to the cache, failing if the key already exists.

   :param key: Location of the value
   :param value: Value to cache
   :param timeout: Number of seconds to hold value in cache.
   :type timeout: Number of seconds or DEFAULT_TIMEOUT
   :rtype: True if object was added and False if it already exists.


.. function:: set(self, key, value, timeout=DEFAULT_TIMEOUT):

    Sets a value to the cache, regardless of whether it exists.

    If ``timeout == None``, then cache is set indefinitely.  Otherwise, timeout defaults to the defined ``DEFAULT_TIMEOUT``.

    :param key: Location of the value
    :param value: Value to cache
    :param timeout: Number of seconds to hold value in cache.
    :type timeout: Number of seconds or DEFAULT_TIMEOUT


.. function:: delete(self, key):

    Removes a key from the cache

    :param key: Location of the value


.. function:: delete_many(self, keys[, version=None]):

    Removes multiple keys at once.

    :param key: Location of the value
    :param version: Version of keys


.. function:: clear(self[, version=None]):

    Flushes the cache.  If version is provided, all keys under the version number will be deleted. Otherwise, all keys will be flushed.

    :param version:  Version of keys


.. function:: get_many(self, keys[, version=None]):

    Retrieves many keys at once.

    :param keys: an iterable of keys to retrieve.
    :rtype: Dict of keys mapping to their values.


.. function:: set_many(self, data[, timeout=None, version=None]):

    Set many values in the cache at once from a dict of key/value pairs. This is much more efficient than calling set() multiple times and is atomic.

    :param data: dict of key/value pairs to cache.
    :param timeout: Number of seconds to hold value in cache.
    :type timeout: Number of seconds or None


.. function:: incr(self, key[, delta=1]):

    Add delta to value in the cache. If the key does not exist, raise a `ValueError` exception.

    :param key: Location of the value
    :param delta: Integer used to increment a value.
    :type delta: Integer

.. function:: incr_version(self, key[, delta=1, version=None]):

    Adds delta to the cache version for the supplied key. Returns the new version.

    :param key: Location of the value
    :param delta: Integer used to increment a value.
    :type delta: Integer
    :param version: Version of key
    :type version: Integer or None

.. function:: touch(self, key, timeout):

    Updates the timeout on a key.

    :param key: Location of the value
    :rtype: bool



Cache Methods Provided by django-redis-cache
--------------------------------------------


.. function:: has_key(self, key):

    Returns True if the key is in the cache and has not expired.

    :param key: Location of the value
    :rtype: bool


.. function:: ttl(self, key):

    Returns the 'time-to-live' of a key.  If the key is not volatile, i.e. it has not set an expiration, then the value returned is None.
    Otherwise, the value is the number of seconds remaining.  If the key does not exist, 0 is returned.

    :param key: Location of the value
    :rtype: Integer or None


.. function:: delete_pattern(pattern[, version=None]):

    Deletes keys matching the glob-style pattern provided.

    :param pattern: Glob-style pattern used to select keys to delete.
    :param version: Version of the keys


.. function:: get_or_set(self, key, func[, timeout=None, lock_timeout=None, stale_cache_timeout=None]):

    Get a value from the cache or call ``func`` to set it and return it.

    This implementation is slightly more advanced that Django's.  It provides thundering herd
    protection, which prevents multiple threads/processes from calling the value-generating
    function at the same time.

    :param key: Location of the value
    :param func: Callable used to set the value if key does not exist.
    :param timeout: Time in seconds that value at key is considered fresh.
    :type timeout: Number of seconds or None
    :param lock_timeout: Time in seconds that the lock will stay active and prevent other threads from acquiring the lock.
    :type lock_timeout: Number of seconds or None
    :param stale_cache_timeout: Time in seconds that the stale cache will remain after the key has expired. If ``None`` is specified, the stale value will remain indefinitely.
    :type stale_cache_timeout: Number of seconds or None


.. function:: reinsert_keys(self):

    Helper function to reinsert keys using a different pickle protocol version.


.. function:: persist(self, key):

    Removes the timeout on a key.

    Equivalent to setting a timeout of None in a set command.
    :param key: Location of the value
    :rtype: bool

.. function:: lock(self, key, timeout=None, sleep=0.1, blocking_timeout=None, thread_local=True)

    See docs for `redis-py`_.


.. _redis-py: https://redis-py.readthedocs.io/en/latest/_modules/redis/client.html#Redis.lock
