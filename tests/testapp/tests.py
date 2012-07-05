# -*- coding: utf-8 -*-

import time

try:
    import cPickle as pickle
except ImportError:
    import pickle
from django.conf import settings
from django.core.cache import get_cache
from django.test import TestCase
from models import Poll, expensive_calculation
from redis_cache.cache import RedisCache, ImproperlyConfigured, pool
from redis.connection import UnixDomainSocketConnection
from redis.server import server


# functions/classes for complex data type tests
def f():
    return 42


class C:
    def m(n):
        return 24


class RedisCacheTests(TestCase):
    """
    A common set of tests derived from Django's own cache tests

    """
    def setUp(self):
        # use DB 16 for testing and hope there isn't any important data :->
        self.reset_pool()
        self.cache = self.get_cache()

    def tearDown(self):
        # Sometimes it will be necessary to skip this method because we need to test default
        # initialization and that may be using a different port than the test redis server.
        if hasattr(self, '_skip_tearDown') and self._skip_tearDown:
            self._skip_tearDown = False
            return
        self.cache.clear()

    def reset_pool(self):
        if hasattr(self, 'cache'):
            for client in self.cache.clients:
                client.connection_pool.disconnect()

    def get_cache(self, backend=None):
        return get_cache(backend or 'default')

    def test_bad_db_initialization(self):
        self.assertRaises(ImproperlyConfigured, self.get_cache, 'redis_cache.cache://%s:%s?db=not_a_number' % (server.host, server.port))

    def test_bad_port_initialization(self):
        self.assertRaises(ImproperlyConfigured, self.get_cache, 'redis_cache.cache://%s:not_a_number?db=15' % server.host)

    def test_default_initialization(self):
        self.reset_pool()
        self.cache = self.get_cache()
        client = self.cache.clients[0]
        connection_class = client.connection_pool.connection_class
        if connection_class is not UnixDomainSocketConnection:
            self.assertEqual(client.connection_pool.connection_kwargs['host'], '127.0.0.1')
            self.assertEqual(client.connection_pool.connection_kwargs['port'], 6379)
            self._skip_tearDown = True
        self.assertEqual(client.connection_pool.connection_kwargs['db'], 15)

    def test_simple(self):
        # Simple cache set/get works
        self.cache.set("key", "value")
        self.assertEqual(self.cache.get("key"), "value")

    def test_add(self):
        # A key can be added to a cache
        self.cache.add("addkey1", "value")
        result = self.cache.add("addkey1", "newvalue")
        self.assertEqual(result, False)
        self.assertEqual(self.cache.get("addkey1"), "value")

    def test_non_existent(self):
        # Non-existent cache keys return as None/default
        # get with non-existent keys
        self.assertEqual(self.cache.get("does_not_exist"), None)
        self.assertEqual(self.cache.get("does_not_exist", "bang!"), "bang!")

    def test_get_many(self):
        # Multiple cache keys can be returned using get_many
        self.cache.set('a', 'a')
        self.cache.set('b', 'b')
        self.cache.set('c', 'c')
        self.cache.set('d', 'd')
        self.assertEqual(self.cache.get_many(['a', 'c', 'd']), {'a': 'a', 'c': 'c', 'd': 'd'})
        self.assertEqual(self.cache.get_many(['a', 'b', 'e']), {'a': 'a', 'b': 'b'})

    def test_get_many_with_manual_integer_insertion(self):
        keys = ['a', 'b', 'c', 'd']
        for i, key in enumerate(keys):
            self.cache.set(key, i)
        self.assertEqual(self.cache.get_many(keys), {'a': 0, 'b': 1, 'c': 2, 'd': 3})

    def test_get_many_with_automatic_integer_insertion(self):
        keys = ['a', 'b', 'c', 'd']
        for i, key in enumerate(keys):
            self.cache.set(key, i)
        self.assertEqual(self.cache.get_many(keys), {'a': 0, 'b': 1, 'c': 2, 'd': 3})

    def test_delete(self):
        # Cache keys can be deleted
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.assertEqual(self.cache.get("key1"), "spam")
        self.cache.delete("key1")
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), "eggs")

    def test_has_key(self):
        # The cache can be inspected for cache keys
        self.cache.set("hello1", "goodbye1")
        self.assertEqual("hello1" in self.cache, True)
        self.assertEqual("goodbye1" in self.cache, False)

    def test_in(self):
        # The in operator can be used to inspet cache contents
        self.cache.set("hello2", "goodbye2")
        self.assertEqual("hello2" in self.cache, True)
        self.assertEqual("goodbye2" in self.cache, False)

    def test_incr(self):
        # Cache values can be incremented
        self.cache.set('answer', 41)
        self.assertEqual(self.cache.get('answer'), 41)
        self.assertEqual(self.cache.incr('answer'), 42)
        self.assertEqual(self.cache.get('answer'), 42)
        self.assertEqual(self.cache.incr('answer', 10), 52)
        self.assertEqual(self.cache.get('answer'), 52)
        self.assertRaises(ValueError, self.cache.incr, 'does_not_exist')

    def test_decr(self):
        # Cache values can be decremented
        self.cache.set('answer', 43)
        self.assertEqual(self.cache.decr('answer'), 42)
        self.assertEqual(self.cache.get('answer'), 42)
        self.assertEqual(self.cache.decr('answer', 10), 32)
        self.assertEqual(self.cache.get('answer'), 32)
        self.assertRaises(ValueError, self.cache.decr, 'does_not_exist')

    def test_data_types(self):
        # Many different data types can be cached
        stuff = {
            'string': 'this is a string',
            'int': 42,
            'list': [1, 2, 3, 4],
            'tuple': (1, 2, 3, 4),
            'dict': {'A': 1, 'B': 2},
            'function': f,
            'class': C,
        }
        self.cache.set("stuff", stuff)
        self.assertEqual(self.cache.get("stuff"), stuff)

    def test_cache_read_for_model_instance(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        my_poll = Poll.objects.create(question="Well?")
        self.assertEqual(Poll.objects.count(), 1)
        pub_date = my_poll.pub_date
        self.cache.set('question', my_poll)
        cached_poll = self.cache.get('question')
        self.assertEqual(cached_poll.pub_date, pub_date)
        # We only want the default expensive calculation run once
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_write_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache write
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.all().defer('question')
        self.assertEqual(defer_qs.count(), 1)
        self.assertEqual(expensive_calculation.num_runs, 1)
        self.cache.set('deferred_queryset', defer_qs)
        # cache set should not re-evaluate default functions
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_read_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.all().defer('question')
        self.assertEqual(defer_qs.count(), 1)
        self.cache.set('deferred_queryset', defer_qs)
        self.assertEqual(expensive_calculation.num_runs, 1)
        runs_before_cache_read = expensive_calculation.num_runs
        self.cache.get('deferred_queryset')
        # We only want the default expensive calculation run on creation and set
        self.assertEqual(expensive_calculation.num_runs, runs_before_cache_read)

    def test_expiration(self):
        # Cache values can be set to expire
        self.cache.set('expire1', 'very quickly', 1)
        self.cache.set('expire2', 'very quickly', 1)
        self.cache.set('expire3', 'very quickly', 1)

        time.sleep(2)
        self.assertEqual(self.cache.get("expire1"), None)

        self.cache.add("expire2", "newvalue")
        self.assertEqual(self.cache.get("expire2"), "newvalue")
        self.assertEqual("expire3" in self.cache, False)

    def test_set_expiration_timeout_None(self):
        key, value = self.cache.make_key('key'), 'value'
        self.cache.set(key, value)
        self.assertTrue(self.cache.get_client(key).ttl(key) > 0)

    def test_set_expiration_timeout_zero(self):
        key, value = self.cache.make_key('key'), 'value'
        self.cache.set(key, value, timeout=0)
        self.assertTrue(self.cache.get_client(key).ttl(key) is None)
        self.assertTrue(key in self.cache)

    def test_set_expiration_timeout_negative(self):
        key, value = self.cache.make_key('key'), 'value'
        self.cache.set(key, value, timeout=-1)
        self.assertTrue(self.cache.get_client(key).ttl(key) is None)
        self.assertFalse(key in self.cache)

    def test_unicode(self):
        # Unicode values can be cached
        stuff = {
            u'ascii': u'ascii_value',
            u'unicode_ascii': u'Iñtërnâtiônàlizætiøn1',
            u'Iñtërnâtiônàlizætiøn': u'Iñtërnâtiônàlizætiøn2',
            u'ascii': {u'x': 1}
        }
        for (key, value) in stuff.items():
            self.cache.set(key, value)
            self.assertEqual(self.cache.get(key), value)

    def test_binary_string(self):
        # Binary strings should be cachable
        from zlib import compress, decompress
        value = 'value_to_be_compressed'
        compressed_value = compress(value)
        self.cache.set('binary1', compressed_value)
        compressed_result = self.cache.get('binary1')
        self.assertEqual(compressed_value, compressed_result)
        self.assertEqual(value, decompress(compressed_result))

    def test_set_many(self):
        # Multiple keys can be set using set_many
        self.cache.set_many({"key1": "spam", "key2": "eggs"})
        self.assertEqual(self.cache.get("key1"), "spam")
        self.assertEqual(self.cache.get("key2"), "eggs")

    def test_set_many_expiration(self):
        # set_many takes a second ``timeout`` parameter
        self.cache.set_many({"key1": "spam", "key2": "eggs"}, 1)
        time.sleep(2)
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)

    def test_delete_many(self):
        # Multiple keys can be deleted using delete_many
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.cache.set("key3", "ham")
        self.cache.delete_many(["key1", "key2"])
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)
        self.assertEqual(self.cache.get("key3"), "ham")

    def test_clear(self):
        # The cache can be emptied using clear
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.cache.clear()
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)

    def test_long_timeout(self):
        """
        Using a timeout greater than 30 days makes memcached think
        it is an absolute expiration timestamp instead of a relative
        offset. Test that we honour this convention. Refs #12399.
        """
        self.cache.set('key1', 'eggs', 60 * 60 * 24 * 30 + 1)  # 30 days + 1 second
        self.assertEqual(self.cache.get('key1'), 'eggs')

        self.cache.add('key2', 'ham', 60 * 60 * 24 * 30 + 1)
        self.assertEqual(self.cache.get('key2'), 'ham')

        self.cache.set_many({'key3': 'sausage', 'key4': 'lobster bisque'}, 60 * 60 * 24 * 30 + 1)
        self.assertEqual(self.cache.get('key3'), 'sausage')
        self.assertEqual(self.cache.get('key4'), 'lobster bisque')

    def test_incr_version(self):
        if isinstance(self.cache, RedisCache):
            key = "key1"
            self.cache.set(key, "spam", version=1)
            self.assertEqual(self.cache.make_key(key), ':1:key1')
            new_version = self.cache.incr_version(key, 1)
            self.assertEqual(new_version, 2)
            new_key = self.cache.make_key(key, version=new_version)
            self.assertEqual(new_key, ':2:key1')
            self.assertEqual(self.cache.get(key, version=1), None)
            self.assertEqual(self.cache.get(key, version=2), 'spam')

    def test_incr_with_pickled_integer(self):
        "Testing case where there exists a pickled integer and we increment it"
        number = 42
        key = self.cache.make_key("key")
        # manually set value using the redis client
        self.cache.get_client("key").set(key, pickle.dumps(number))
        new_value = self.cache.incr(key)
        self.assertEqual(new_value, number + 1)

        # Test that the pickled value was converted to an integer
        value = int(self.cache.get_client(key).get(key))
        self.assertTrue(isinstance(value, int))

        # now that the value is an integer, let's increment it again.
        new_value = self.cache.incr(key, 7)
        self.assertEqual(new_value, number + 8)

    def test_pickling_cache_object(self):
        p = pickle.dumps(self.cache)
        cache = pickle.loads(p)
        # Now let's do a simple operation using the unpickled cache object
        cache.add("addkey1", "value")
        result = cache.add("addkey1", "newvalue")
        self.assertEqual(result, False)
        self.assertEqual(cache.get("addkey1"), "value")

    def test_float_caching(self):
        self.cache.set('a', 1.1)
        a = self.cache.get('a')
        self.assertEqual(a, 1.1)

    def test_string_float_caching(self):
        self.cache.set('a', '1.1')
        a = self.cache.get('a')
        self.assertEqual(a, 1.1)

    def test_multiple_connection_pool_connections(self):
        pool._connection_pools = {}
        options = settings.CACHES['default']['OPTIONS']
        get_cache('redis_cache.cache.RedisCache', LOCATION="%s:%s" % (server.host, server.port), OPTIONS=options)
        self.assertEqual(len(pool._connection_pools), 1)

        options['DB'] = 14
        get_cache('redis_cache.RedisCache', LOCATION="%s:%s" % (server.host, server.port), OPTIONS=options)
        self.assertEqual(len(pool._connection_pools), 2)

        options['DB'] = 15
        get_cache('redis_cache.RedisCache', LOCATION="%s:%s" % (server.host, server.port), OPTIONS=options)
        self.assertEqual(len(pool._connection_pools), 2)

    def test_delete_pattern(self):
        data = {
            'a': 'a',
            'b': 'b',
            'aa': 'aa',
            'bb': 'bb',
            'aaa': 'aaa',
            'bbb': 'bbb',
        }
        self.cache.set_many(data)
        self.cache.delete_pattern('aa*')
        items = self.cache.get_many(data.keys())
        self.assertEqual(len(items), 4)

        self.cache.delete_pattern('b?b')
        items = self.cache.get_many(data.keys())
        self.assertEqual(len(items), 3)

    def test_clearing_using_version(self):
        self.cache.set('a', 'a', version=1)
        self.cache.set('b', 'b', version=1)
        self.cache.set('a', 'a', version=2)
        self.cache.set('b', 'b', version=2)

        values = self.cache.get_many(['a', 'b'], version=1)
        self.assertEqual(len(values), 2)

        values = self.cache.get_many(['a', 'b'], version=2)
        self.assertEqual(len(values), 2)

        self.cache.clear(version=2)

        values = self.cache.get_many(['a', 'b'], version=1)
        self.assertEqual(len(values), 2)

        values = self.cache.get_many(['a', 'b'], version=2)
        self.assertEqual(len(values), 0)
