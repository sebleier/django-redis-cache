import time

from django.core.cache import caches
from django.test import TestCase, override_settings

from redis_cache.connection import pool

from tests.testapp.tests.base_tests import SetupMixin


MASTER_LOCATION = "127.0.0.1:6387"
LOCATIONS = [
    '127.0.0.1:6387',
    '127.0.0.1:6388',
    '127.0.0.1:6389',
]


@override_settings(CACHES={
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': LOCATIONS,
        'OPTIONS': {
            'DB': 1,
            'PASSWORD': 'yadayada',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'PICKLE_VERSION': -1,
            'MASTER_CACHE': MASTER_LOCATION,
        },
    },
})
class MasterSlaveTestCase(SetupMixin, TestCase):

    def setUp(self):
        super(MasterSlaveTestCase, self).setUp()
        pool.reset()

    def test_master_client(self):
        # Reset the caches at the beginning of the test.
        caches._caches.caches = {}

        cache = self.get_cache()
        client = cache.master_client
        self.assertEqual(
            client.connection_pool.connection_identifier,
            ('127.0.0.1', 6387, 1, None)
        )
        self.assertEqual(len(pool._connection_pools), 3)

    def test_set(self):
        cache = self.get_cache()
        cache.set('a', 'a')
        time.sleep(.2)
        for client in self.cache.clients.values():
            key = cache.make_key('a')
            self.assertIsNotNone(client.get(key))

    def test_set_many(self):
        cache = self.get_cache()
        cache.set_many({'a': 'a', 'b': 'b'})
        for client in self.cache.clients.values():
            self.assertNotIn(None, client.mget([
                cache.make_key('a'),
                cache.make_key('b'),
            ]))

    def test_incr(self):
        cache = self.get_cache()
        cache.set('a', 0)
        cache.incr('a')
        time.sleep(.2)
        key = cache.make_key('a')
        for client in self.cache.clients.values():
            self.assertEqual(int(client.get(key)), 1)

    def test_delete(self):
        cache = self.get_cache()
        cache.set('a', 'a')
        time.sleep(.2)
        self.assertEqual(cache.get('a'), 'a')
        cache.delete('a')
        time.sleep(.2)
        key = cache.make_key('a')
        for client in self.cache.clients.values():
            self.assertIsNone(client.get(key))

    def test_clear(self):
        cache = self.get_cache()
        cache.set('a', 'a')
        time.sleep(.2)
        self.assertEqual(cache.get('a'), 'a')
        cache.clear()
        time.sleep(.2)
        for client in self.cache.clients.values():
            self.assertEqual(len(client.keys('*')), 0)
