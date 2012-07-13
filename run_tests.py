#!/usr/bin/env python
from __future__ import with_statement
from optparse import OptionParser
import os
from os.path import dirname, abspath, join
import sys
from django import VERSION
from django.conf import settings
from django.template import Template, Context
from django.utils import importlib
from django.core.cache import get_cache
from redis_cache.server import RedisServer
from redis import Redis
from redis.exceptions import ResponseError


def load_settings(module):
    try:
        mod = importlib.import_module(module)
    except (ImportError):
        return None

    conf = {}
    for setting in dir(mod):
        if setting == setting.upper():
            conf[setting] = getattr(mod, setting)
    return conf


class TmpFile(object):
    def __init__(self, path, contents):
        self.path = path
        self.contents = contents

    def __enter__(self):
        self.file = open(self.path, "w")
        self.file.write(self.contents)
        self.file.close()

    def __exit__(self, exc_type, exc_value, traceback):
        os.remove(self.path)


def reset_settings():
    """
    This is hack to allow settings to be configured again.
    """
    if VERSION >= (1, 4, 0):
        from django.utils.functional import empty
        settings._wrapped = empty
    else:
        settings._wrapped = None


def _runtests(host, ports, password=None):
    from django.test.simple import DjangoTestSuiteRunner
    for port in ports:
        client = Redis(host, port)
        try:
            client.config_set('requirepass', password)
        except ResponseError:
            client = Redis(host, port, password=password)
            client.config_set('requirepass', password)
    runner = DjangoTestSuiteRunner(verbosity=options.verbosity, interactive=True, failfast=False)
    return runner.run_tests(['testapp'])


def runtests(options):
    os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    redis_version = options.redis_version
    is_sockets_test = options.settings == "tests.sockets_settings"

    conf = load_settings(options.settings)
    if conf is None:
        sys.stderr.write('Cannot load settings module: %s\n' % options.settings)
        return sys.exit(1)

    # If server path was not specified, then assume an instance of redis with
    # default configuration is running
    if options.server_path is None:
        sys.stderr.write('Tests must be run by specifying where the redis-server executable is located.\n')
        sys.exit(1)

    redis_conf_path = join(dirname(__file__), 'tests', 'redis.conf')

    try:
        redis_conf_template = open(join(dirname(__file__), 'tests', 'redis.conf.%s' % redis_version)).read()
    except (OSError, IOError):
        sys.stderr.write('Cannot find template for redis.conf.\n')

    context = Context({
        'redis_socket': join(dirname(abspath(__file__)), 'tests', 'redis.sock')
    })
    contents = Template(redis_conf_template).render(context)

    with TmpFile(redis_conf_path, contents):
        if not is_sockets_test:
            conf['CACHES']['default']['LOCATION'] = [
                "%s:%s" % ('127.0.0.1', '6380'),
                "%s:%s" % ('127.0.0.1', '6381'),
                "%s:%s" % ('127.0.0.1', '6382'),
            ]
            reset_settings()
            settings.configure(**conf)

        # Start 3 servers running in sequential ports
        with RedisServer(options.server_path, redis_conf_path, {'port': '6380'}):
            with RedisServer(options.server_path, redis_conf_path, {'port': '6381'}):
                with RedisServer(options.server_path, redis_conf_path, {'port': '6382'}):
                    failures = _runtests('127.0.0.1', [6380, 6381, 6382], 'yadayada')

    sys.exit(failures)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-s", "--server", dest="server_path", action="store",
        type="string", default=None, help="Path to the redis server executable")
    parser.add_option("-v", "--verbosity", dest="verbosity", default=1, type="int",
        help="Change the verbostiy of the redis-server.")
    parser.add_option("--settings", dest="settings", default="tests.python_parser_settings",
        help="Django settings module to use for the tests.")
    parser.add_option("--redis-version", dest="redis_version", default="2.6", help="Redis version")

    (options, args) = parser.parse_args()

    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)

    runtests(options)
