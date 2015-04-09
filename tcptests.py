#!/usr/bin/env python
import sys
from os.path import dirname, abspath, join
import django
from django.conf import settings


cache_settings = {
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    'MIDDLEWARE_CLASSES':(),
    'INSTALLED_APPS': [
        'testapp',
    ],
    'ROOT_URLCONF': 'tests.urls',
    'CACHES': {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': '127.0.0.1:6379',
            'OPTIONS': {
                'DB': 15,
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'CONNECTION_POOL_CLASS': 'redis.ConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 2
                }
            },
        },
    },
}


if not settings.configured:
    settings.configure(**cache_settings)

try:
    from django.test.simple import DjangoTestSuiteRunner as TestSuiteRunner
except ImportError:
    from django.test.runner import DiscoverRunner as TestSuiteRunner


def runtests(*test_args):
    if not test_args:
        test_args = ['testapp']
    sys.path.insert(0, join(dirname(abspath(__file__)), 'tests'))
    try:
        django.setup()
    except AttributeError:
        pass
    runner = TestSuiteRunner(verbosity=1, interactive=True, failfast=False)
    failures = runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    runtests(*sys.argv[1:])
