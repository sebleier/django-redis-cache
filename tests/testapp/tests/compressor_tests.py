# -*- coding: utf-8 -*-
from django.test import TestCase, override_settings

from tests.testapp.tests.base_tests import BaseRedisTestCase

LOCATION = "127.0.0.1:6381"


class CompressionTestCase(object):

    def test_compression(self):
        key = 'a'
        noop_cache = self.get_cache('noop')
        string = 10000 * 'a'

        self.cache.set(key, string)
        noop_cache.set(key, string)
        self.assertEqual(self.cache.get(key), noop_cache.get(key))
        self.assertNotEqual(self.cache, noop_cache)

        noop_client, = list(noop_cache.clients.values())
        default_client, = list(self.cache.clients.values())
        versioned_key = self.cache.make_key(key)
        self.assertLess(
            len(default_client.get(versioned_key)),
            len(noop_client.get(versioned_key)),
        )


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': LOCATION,
            'OPTIONS': {
                'DB': 14,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': -1,
                'COMPRESSOR_CLASS': 'redis_cache.compressors.ZLibCompressor',
                'COMPRESSOR_CLASS_KWARGS': {
                    'level': 5,
                },
                'CONNECTION_POOL_CLASS': 'redis.ConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 2,
                },
            },
        },
        'noop': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': LOCATION,
            'OPTIONS': {
                'DB': 15,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': -1,
                'COMPRESSOR_CLASS': 'redis_cache.compressors.NoopCompressor',
            },
        },
    }
)
class ZLibTestCase(CompressionTestCase, BaseRedisTestCase, TestCase):
    pass


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': LOCATION,
            'OPTIONS': {
                'DB': 14,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': -1,
                'COMPRESSOR_CLASS': 'redis_cache.compressors.BZip2Compressor',
                'COMPRESSOR_CLASS_KWARGS': {
                    'compresslevel': 5,
                },
                'CONNECTION_POOL_CLASS': 'redis.ConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 2,
                },
            },
        },
        'noop': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': LOCATION,
            'OPTIONS': {
                'DB': 15,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': -1,
                'COMPRESSOR_CLASS': 'redis_cache.compressors.NoopCompressor',
            },
        },
    }
)
class BZip2TestCase(CompressionTestCase, BaseRedisTestCase, TestCase):
    pass
