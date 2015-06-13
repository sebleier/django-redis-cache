# # -*- coding: utf-8 -*-
from tests.testapp.tests.base_tests import BaseRedisTestCase
from tests.testapp.tests.multi_server_tests import MultiServerTests

try:
    from django.test import override_settings
except ImportError:
    from django.test.utils import override_settings
from django.test import TestCase

from redis_cache.cache import ImproperlyConfigured
from redis.connection import UnixDomainSocketConnection


LOCATION = "unix://:yadayada@/tmp/redis4.sock?db=15"
LOCATIONS = [
    "unix://:yadayada@/tmp/redis4.sock?db=15",
    "unix://:yadayada@/tmp/redis5.sock?db=15",
    "unix://:yadayada@/tmp/redis6.sock?db=15",
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
    pass


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

