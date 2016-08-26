# # -*- coding: utf-8 -*-
from collections import Counter
from tests.testapp.tests.base_tests import BaseRedisTestCase
from tests.testapp.tests.multi_server_tests import MultiServerTests

from django.test import TestCase, override_settings


LOCATION = "unix://:yadayada@/tmp/redis0.sock?db=15"
LOCATIONS = [
    "unix://:yadayada@/tmp/redis0.sock?db=15",
    "unix://:yadayada@/tmp/redis1.sock?db=15",
    "unix://:yadayada@/tmp/redis2.sock?db=15",
]


class SocketTestCase(BaseRedisTestCase, TestCase):
    pass


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': LOCATION,
            'OPTIONS': {
                'DB': 15,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': 2,
                'CONNECTION_POOL_CLASS': 'redis.ConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 2,
                }
            },
        },
    }
)
class SingleHiredisTestCase(SocketTestCase):
    pass


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': LOCATION,
            'OPTIONS': {
                'DB': 15,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.PythonParser',
                'PICKLE_VERSION': 2,
                'CONNECTION_POOL_CLASS': 'redis.ConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 2,
                }
            },
        },
    }
)
class SinglePythonParserTestCase(SocketTestCase):
    pass


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'redis_cache.ShardedRedisCache',
            'LOCATION': LOCATIONS,
            'OPTIONS': {
                'DB': 15,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': 2,
                'CONNECTION_POOL_CLASS': 'redis.ConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 2,
                }
            },
        },
    }
)
class MultipleHiredisTestCase(MultiServerTests, SocketTestCase):

    def test_equal_number_of_nodes(self):
        counter = Counter(
            [node._node[3] for node in self.cache.sharder._nodes]
        )
        self.assertEqual(counter, {
            '/tmp/redis0.sock': 16,
            '/tmp/redis1.sock': 16,
            '/tmp/redis2.sock': 16,
        })


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'redis_cache.ShardedRedisCache',
            'LOCATION': LOCATIONS,
            'OPTIONS': {
                'DB': 15,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.PythonParser',
                'PICKLE_VERSION': 2,
                'CONNECTION_POOL_CLASS': 'redis.ConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 2,
                }
            },
        },
    }
)
class MultiplePythonParserTestCase(MultiServerTests, SocketTestCase):
    pass
