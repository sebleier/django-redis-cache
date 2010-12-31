import warnings
from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
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


class CacheClass(BaseCache):
    def __init__(self, server, params):
        """
        Connect to Redis, and sets up cache backend.
        
        Additional params:
            
                key:            ``db``
                type:           ``int``
                default:        ``1``
                description:    ``Specifies redis db number to use``
            
                key:            ``fail_silently``
                type:           ``int``
                default:        ``0``
                description:    ``When non-zero integer, swallows exceptions, emitting them as warnings instead. Allows cache
                                  server to go down without killing the site``
            
        """
        BaseCache.__init__(self, params)
        
        db = params.get('db', 1)
        try:
            db = int(db)
        except (ValueError, TypeError):
            db = 1
        
        fail_silently = params.get('fail_silently', 0)
        try:
            self.fail_silently = bool(int(fail_silently))
        except (ValueError, TypeError):
            self.fail_silently = False
        
        password = params.get('password', None)
        if ':' in server:
            host, port = server.split(':')
            try:
                port = int(port)
            except (ValueError, TypeError):
                port = 6379
        else:
            host = 'localhost'
            port = 6379

        try:
            self._cache = redis.Redis(host=host, port=port, db=db, password=password)
        except Exception as err:
            self.warn_or_error(err)
    
    def warn_or_error(self, exception, default_return_value=None):
        """
        Emits a warning and returns a default value, or re-raises an Exception depending on cache configuration options.
        """
        if not self.fail_silently:
            raise exception

        warnings.warn(str(exception), RuntimeWarning)
        return default_return_value
        

    def prepare_key(self, key):
        """
        Returns the utf-8 encoded bytestring of the given key.
        """
        return smart_str(key)

    def add(self, key, value, timeout=None):
        """
        Add a value to the cache, failing if the key already exists.

        Returns ``True`` if the object was added, ``False`` if not.
        """
        try:
            key = self.prepare_key(key)
            if self._cache.exists(key):
                return False
            return self.set(key, value, timeout)
        except Exception as err:
            return self.warn_or_error(err, False)

    def get(self, key, default=None):
        """
        Retrieve a value from the cache.

        Returns unpicked value if key is found, ``None`` if not.
        """
        try:
            # get the value from the cache
            value = self._cache.get(self.prepare_key(key))
            if value is None:
                return default
            # pickle doesn't want a unicode!
            value = smart_str(value)
            # hydrate that pickle
            return pickle.loads(value)
        except Exception as err:
            return self.warn_or_error(err)

    def set(self, key, value, timeout=None):
        """
        Persist a value to the cache, and set an optional expiration time.
        """
        try:
            key = self.prepare_key(key)
            # store the pickled value
            result = self._cache.set(key, pickle.dumps(value))
            # set expiration if needed
            self.expire(key, timeout)
            # result is a boolean
            return result
        except Exception as err:
            return self.warn_or_error(err, False)

    def expire(self, key, timeout=None):
        """
        Set content expiration, if necessary
        """
        try:
            if timeout == 0:
                # force the key to be non-volatile
                result = self._cache.get(key)
                self._cache.set(key, result)
            else:
                timeout = timeout or self.default_timeout
                # If the expiration command returns false, we need to reset the key
                # with the new expiration
                if not self._cache.expire(key, timeout):
                    value = self.get(key)
                    self.set(key, value, timeout)
        except Exception as err:
            return self.warn_or_error(err)

    def delete(self, key):
        """
        Remove a key from the cache.
        """
        try:
            self._cache.delete(self.prepare_key(key))
        except Exception as err:
            return self.warn_or_error(err)

    def delete_many(self, keys):
        """
        Remove multiple keys at once.
        """
        try:
            if keys:
                self._cache.delete(*map(self.prepare_key, keys))
        except Exception as err:
            return self.warn_or_error(err)

    def clear(self):
        """
        Flush all cache keys.
        """
        try:
            self._cache.flushdb()
        except Exception as err:
            return self.warn_or_error(err)

    def get_many(self, keys):
        """
        Retrieve many keys.
        """
        try:
            recovered_data = SortedDict()
            results = self._cache.mget(map(lambda k: self.prepare_key(k), keys))
            for key, value in zip(keys, results):
                if value is None:
                    continue
                # pickle doesn't want a unicode!
                value = smart_str(value)
                # hydrate that pickle
                value = pickle.loads(value)
                if isinstance(value, basestring):
                    value = smart_unicode(value)
                recovered_data[key] = value
            return recovered_data
        except Exception as err:
            return self.warn_or_error(err, recovered_data)

    def set_many(self, data, timeout=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        try:
            safe_data = {}
            for key, value in data.iteritems():
                safe_data[self.prepare_key(key)] = pickle.dumps(value)
            if safe_data:
                self._cache.mset(safe_data)
                map(self.expire, safe_data, [timeout]*len(safe_data))
        except Exception as err:
            return self.warn_or_error(err)


        
    def close(self, **kwargs):
        """
        Disconnect from the cache.
        """
        try:
            self._cache.connection.disconnect()
        except Exception as err:
            return self.warn_or_error(err)
