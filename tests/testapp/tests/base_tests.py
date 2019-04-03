# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from hashlib import sha1
import os
import subprocess
import threading
import time


try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes

import redis

from tests.testapp.models import Poll, expensive_calculation
from redis_cache.cache import RedisCache, pool
from redis_cache.constants import KEY_EXPIRED, KEY_NON_VOLATILE
from redis_cache.utils import get_servers, parse_connection_kwargs


REDIS_PASSWORD = 'yadayada'


LOCATION = "127.0.0.1:6381"


# functions/classes for complex data type tests
def f():
    return 42


class C:
    def m(n):
        return 24


def start_redis_servers(servers, db=None, master=None):
    """Creates redis instances using specified locations from the settings.

    Returns list of Popen objects
    """
    processes = []
    devnull = open(os.devnull, 'w')
    master_connection_kwargs = master and parse_connection_kwargs(
        master,
        db=db,
        password=REDIS_PASSWORD
    )
    for i, server in enumerate(servers):
        connection_kwargs = parse_connection_kwargs(
            server,
            db=db,
            password=REDIS_PASSWORD,  # will be overridden if specified in `server`
        )
        parameters = dict(
            port=connection_kwargs.get('port', 0),
            requirepass=connection_kwargs['password'],
        )
        is_socket = server.startswith('unix://') or server.startswith('/')
        if is_socket:
            parameters.update(
                port=0,
                unixsocket='/tmp/redis{0}.sock'.format(i),
                unixsocketperm=755,
            )
        if master and not connection_kwargs == master_connection_kwargs:
            parameters.update(
                masterauth=master_connection_kwargs['password'],
                slaveof="{host} {port}".format(
                    host=master_connection_kwargs['host'],
                    port=master_connection_kwargs['port'],
                )
            )

        args = ['./redis/src/redis-server'] + [
            "--{parameter} {value}".format(parameter=parameter, value=value)
            for parameter, value in parameters.items()
        ]
        p = subprocess.Popen(args, stdout=devnull)
        processes.append(p)

    return processes


class SetupMixin(object):
    processes = None

    @classmethod
    def tearDownClass(cls):
        for p in cls.processes:
            p.kill()
        cls.processes = None

        # Give redis processes some time to shutdown
        # time.sleep(.1)

    def setUp(self):
        if self.__class__.processes is None:
            from django.conf import settings

            cache_settings = settings.CACHES['default']
            servers = get_servers(cache_settings['LOCATION'])
            options = cache_settings.get('OPTIONS', {})
            db = options.get('db', 0)
            master = options.get('MASTER_CACHE')
            self.__class__.processes = start_redis_servers(
                servers,
                db=db,
                master=master
            )

            # Give redis processes some time to startup
            time.sleep(.1)

        self.reset_pool()
        self.cache = self.get_cache()

    def tearDown(self):
        # clear caches to allow @override_settings(CACHES=...) to work.
        caches._caches.caches = {}
        # Sometimes it will be necessary to skip this method because we need to
        # test default initialization and that may be using a different port
        # than the test redis server.
        if hasattr(self, '_skip_tearDown') and self._skip_tearDown:
            self._skip_tearDown = False
            return
        self.cache.clear()

    def reset_pool(self):
        pool.reset()

    def get_cache(self, backend=None):
        return caches[backend or 'default']


class BaseRedisTestCase(SetupMixin):

    def test_simple(self):
        # Simple cache set/get works
        self.cache.set("key", "value")
        self.assertEqual(self.cache.get("key"), "value")

    def test_add(self):
        # A key can be added to a cache
        self.cache.add("addkey1", "value")
        result = self.cache.add("addkey1", "newvalue")
        self.assertFalse(result)
        self.assertEqual(self.cache.get("addkey1"), "value")

    def test_non_existent(self):
        # Non-existent cache keys return as None/default
        # get with non-existent keys
        self.assertIsNone(self.cache.get("does_not_exist"))
        self.assertEqual(self.cache.get("does_not_exist", "bang!"), "bang!")

    def test_get_many(self):
        # Multiple cache keys can be returned using get_many
        self.cache.set('a', 'a')
        self.cache.set('b', 'b')
        self.cache.set('c', 'c')
        self.cache.set('d', 'd')
        self.assertEqual(self.cache.get_many(['a', 'c', 'd']), {'a': 'a', 'c': 'c', 'd': 'd'})
        self.assertEqual(self.cache.get_many(['a', 'b', 'e']), {'a': 'a', 'b': 'b'})

    def test_get_many_works_with_empty_keys_array(self):
        self.assertEqual(self.cache.get_many([]), {})

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
        self.assertIsNone(self.cache.get("key1"))
        self.assertEqual(self.cache.get("key2"), "eggs")

    def test_has_key(self):
        # The cache can be inspected for cache keys
        self.cache.set("hello1", "goodbye1")
        self.assertIn("hello1", self.cache)
        self.assertNotIn("goodbye1", self.cache)

    def test_in(self):
        # The in operator can be used to inspet cache contents
        self.cache.set("hello2", "goodbye2")
        self.assertIn("hello2", self.cache)
        self.assertNotIn("goodbye2", self.cache)

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
        key, value = 'key', 'value'
        self.cache.set(key, value, timeout=None)
        self.assertIsNone(self.cache.ttl(key))

    def test_set_expiration_timeout_zero(self):
        key, value = self.cache.make_key('key'), 'value'
        self.cache.set(key, value, timeout=0)
        self.assertEqual(self.cache.get_client(key).ttl(key), KEY_EXPIRED)
        self.assertNotIn(key, self.cache)

    def test_set_expiration_timeout_negative(self):
        key, value = self.cache.make_key('key'), 'value'
        self.cache.set(key, value, timeout=-1)
        self.assertNotIn(key, self.cache)

    def test_unicode(self):
        # Unicode values can be cached
        stuff = {
            'ascii': 'ascii_value',
            'unicode_ascii': 'Iñtërnâtiônàlizætiøn1',
            'Iñtërnâtiônàlizætiøn': 'Iñtërnâtiônàlizætiøn2',
            'ascii': {'x': 1}
        }
        for (key, value) in stuff.items():
            self.cache.set(key, value)
            self.assertEqual(self.cache.get(key), value)

    def test_binary_string(self):
        # Binary strings should be cachable
        from zlib import compress, decompress
        value = b'value_to_be_compressed'
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

    def test_set_many_works_with_empty_dict(self):
        # This test passes if no exception is raised
        self.cache.set_many({})
        self.cache.set_many({}, version=2)

    def test_set_many_expiration(self):
        # set_many takes a second ``timeout`` parameter
        self.cache.set_many({"key1": "spam", "key2": "eggs"}, 1)
        time.sleep(2)
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))

    def test_set_many_version(self):
        self.cache.set_many({"key1": "spam", "key2": "eggs"}, version=2)
        self.assertEqual(self.cache.get("key1", version=2), "spam")
        self.assertEqual(self.cache.get("key2", version=2), "eggs")

    def test_delete_many(self):
        # Multiple keys can be deleted using delete_many
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.cache.set("key3", "ham")
        self.cache.delete_many(["key1", "key2"])
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))
        self.assertEqual(self.cache.get("key3"), "ham")
        # Test that passing an empty list fails silently
        self.cache.delete_many([])

    def test_clear(self):
        # The cache can be emptied using clear
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.cache.clear()
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))

    def test_long_timeout(self):
        """Using a timeout greater than 30 days makes memcached think
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
            self.assertIsNone(self.cache.get(key, version=1))
            self.assertEqual(self.cache.get(key, version=2), 'spam')

    def test_pickling_cache_object(self):
        p = pickle.dumps(self.cache)
        cache = pickle.loads(p)
        # Now let's do a simple operation using the unpickled cache object
        cache.add("addkey1", "value")
        result = cache.add("addkey1", "newvalue")
        self.assertFalse(result)
        self.assertEqual(cache.get("addkey1"), "value")

    def test_float_caching(self):
        self.cache.set('a', 1.1)
        a = self.cache.get('a')
        self.assertEqual(a, 1.1)

    def test_string_float_caching(self):
        self.cache.set('a', '1.1')
        a = self.cache.get('a')
        self.assertEqual(a, '1.1')

    def test_setting_string_integer_retrieves_string(self):
        self.assertTrue(self.cache.set("foo", "1"))
        self.assertEqual(self.cache.get("foo"), "1")

    def test_setting_bool_retrieves_bool(self):
        self.assertTrue(self.cache.set("bool_t", True))
        self.assertTrue(self.cache.get("bool_t"))
        self.assertTrue(self.cache.set("bool_f", False))
        self.assertFalse(self.cache.get("bool_f"))

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

    def test_reinsert_keys(self):
        self.cache._pickle_version = 0
        for i in range(2000):
            s = sha1(force_bytes(i)).hexdigest()
            self.cache.set(s, self.cache)
        self.cache._pickle_version = -1
        self.cache.reinsert_keys()

    def test_ttl_of_reinsert_keys(self):
        self.cache.set('a', 'a', 5)
        self.assertEqual(self.cache.get('a'), 'a')
        self.cache.set('b', 'b', 5)
        self.cache.reinsert_keys()
        self.assertEqual(self.cache.get('a'), 'a')
        self.assertGreater(self.cache.ttl('a'), 1)
        self.assertEqual(self.cache.get('b'), 'b')
        self.assertGreater(self.cache.ttl('a'), 1)

    def test_get_or_set(self):

        def expensive_function():
            expensive_function.num_calls += 1
            return 42

        expensive_function.num_calls = 0
        self.assertEqual(expensive_function.num_calls, 0)
        value = self.cache.get_or_set('a', expensive_function, 1)
        self.assertEqual(expensive_function.num_calls, 1)
        self.assertEqual(value, 42)

        value = self.cache.get_or_set('a', expensive_function, 1)
        self.assertEqual(expensive_function.num_calls, 1)
        self.assertEqual(value, 42)

        value = self.cache.get_or_set('a', expensive_function, 1)
        self.assertEqual(expensive_function.num_calls, 1)
        self.assertEqual(value, 42)

        time.sleep(2)
        value = self.cache.get_or_set('a', expensive_function, 1)
        self.assertEqual(expensive_function.num_calls, 2)
        self.assertEqual(value, 42)

    def test_get_or_set_serving_from_stale_value(self):

        def expensive_function(x):
            time.sleep(.5)
            expensive_function.num_calls += 1
            return x

        expensive_function.num_calls = 0
        self.assertEqual(expensive_function.num_calls, 0)
        results = {}

        def thread_worker(thread_id, return_value, timeout, lock_timeout, stale_cache_timeout):
            value = self.cache.get_or_set(
                'key',
                lambda: expensive_function(return_value),
                timeout,
                lock_timeout,
                stale_cache_timeout
            )
            results[thread_id] = value

        thread_0 = threading.Thread(target=thread_worker, args=(0, 'a', 1, None, 1))
        thread_1 = threading.Thread(target=thread_worker, args=(1, 'b', 1, None, 1))
        thread_2 = threading.Thread(target=thread_worker, args=(2, 'c', 1, None, 1))
        thread_3 = threading.Thread(target=thread_worker, args=(3, 'd', 1, None, 1))
        thread_4 = threading.Thread(target=thread_worker, args=(4, 'e', 1, None, 1))

        # First thread should complete and return its value
        thread_0.start()  # t = 0, valid from t = .5 - 1.5, stale from t = 1.5 - 2.5

        # Second thread will start while the first thread is still working and return None.
        time.sleep(.25)  # t = .25
        thread_1.start()
        # Third thread will start after the first value is computed, but before it expires.
        # its value.
        time.sleep(.5)  # t = .75
        thread_2.start()
        # Fourth thread will start after the first value has expired and will re-compute its value.
        # valid from t = 2.25 - 3.25, stale from t = 3.75 - 4.75.
        time.sleep(1)  # t = 1.75
        thread_3.start()
        # Fifth thread will start after the fourth thread has started to compute its value, but
        # before the first thread's stale cache has expired.
        time.sleep(.25)  # t = 2
        thread_4.start()

        thread_0.join()
        thread_1.join()
        thread_2.join()
        thread_3.join()
        thread_4.join()

        self.assertEqual(results, {
            0: 'a',
            1: None,
            2: 'a',
            3: 'd',
            4: 'a'
        })

    def assertMaxConnection(self, cache, max_num):
        for client in cache.clients.values():
            self.assertLessEqual(client.connection_pool._created_connections, max_num)

    def test_max_connections(self):
        pool._connection_pools = {}
        cache = caches['default']

        def noop(*args, **kwargs):
            pass

        releases = {}
        for client in cache.clients.values():
            releases[client.connection_pool] = client.connection_pool.release
            client.connection_pool.release = noop
            self.assertEqual(client.connection_pool.max_connections, 2)

        cache.set('a', 'a')
        self.assertMaxConnection(cache, 1)

        cache.set('a', 'a')
        self.assertMaxConnection(cache, 2)

        with self.assertRaises(redis.ConnectionError):
            cache.set('a', 'a')

        self.assertMaxConnection(cache, 2)

        for client in cache.clients.values():
            client.connection_pool.release = releases[client.connection_pool]
            client.connection_pool.max_connections = 2 ** 31

    def test_has_key_with_no_key(self):
        self.assertFalse(self.cache.has_key('does_not_exist'))

    def test_has_key_with_key(self):
        self.cache.set('a', 'a')
        self.assertTrue(self.cache.has_key('a'))

    def test_ttl_set_expiry(self):
        self.cache.set('a', 'a', 10)
        ttl = self.cache.ttl('a')
        self.assertAlmostEqual(ttl, 10)

    def test_ttl_no_expiry(self):
        self.cache.set('a', 'a', timeout=None)
        ttl = self.cache.ttl('a')
        self.assertIsNone(ttl)

    def test_ttl_past_expiry(self):
        self.cache.set('a', 'a', timeout=1)
        ttl = self.cache.ttl('a')
        self.assertAlmostEqual(ttl, 1)

        time.sleep(1.1)

        ttl = self.cache.ttl('a')
        self.assertEqual(ttl, 0)

    def test_non_existent_key(self):
        """Non-existent keys are semantically the same as keys that have
        expired.
        """
        ttl = self.cache.ttl('does_not_exist')
        self.assertEqual(ttl, 0)

    def test_persist_expire_to_persist(self):
        self.cache.set('a', 'a', timeout=10)
        self.cache.persist('a')
        self.assertIsNone(self.cache.ttl('a'))

    def test_touch_no_expiry_to_expire(self):
        self.cache.set('a', 'a', timeout=None)
        self.cache.touch('a', 10)
        ttl = self.cache.ttl('a')
        self.assertAlmostEqual(ttl, 10)

    def test_touch_less(self):
        self.cache.set('a', 'a', timeout=20)
        self.cache.touch('a', 10)
        ttl = self.cache.ttl('a')
        self.assertAlmostEqual(ttl, 10)

    def test_touch_more(self):
        self.cache.set('a', 'a', timeout=10)
        self.cache.touch('a', 20)
        ttl = self.cache.ttl('a')
        self.assertAlmostEqual(ttl, 20)


class ConfigurationTestCase(SetupMixin, TestCase):

    @override_settings(
        CACHES={
            'default': {
                'BACKEND': 'redis_cache.RedisCache',
                'LOCATION': LOCATION,
                'OPTIONS': {
                    'DB': 15,
                    'PASSWORD': 'yadayada',
                    'PARSER_CLASS': 'path.to.unknown.class',
                    'PICKLE_VERSION': 2,
                    'CONNECTION_POOL_CLASS': 'redis.ConnectionPool',
                    'CONNECTION_POOL_CLASS_KWARGS': {
                        'max_connections': 2,
                    }
                },
            },
        }
    )
    def test_bad_parser_import(self):
        with self.assertRaises(ImproperlyConfigured):
            caches['default']


@override_settings(CACHES={
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': [
            'redis://:yadayada@localhost:6381/15',
            'redis://:yadayada@localhost:6382/15',
            'redis://:yadayada@localhost:6383/15',
        ],
        'OPTIONS': {
            'DB': 1,
            'PASSWORD': 'yadayada',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'PICKLE_VERSION': -1,
            'MASTER_CACHE': 'redis://:yadayada@localhost:6381/15',
        },
    },
})
class RedisUrlRegressionTests(SetupMixin, TestCase):

    def test_unix_path_error_using_redis_url(self):
        pass
