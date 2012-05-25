#!/usr/bin/env python
from __future__ import with_statement
from optparse import OptionParser
import os
from os.path import dirname, abspath, join
import sys
from django.conf import settings
from django.template import Template, Context
from django.utils import importlib
from redis.server import server


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
        self.path =path
        self.contents = contents

    def __enter__(self):
        self.file = open(self.path, "w")
        self.file.write(self.contents)
        self.file.close()

    def __exit__(self, exc_type, exc_value, traceback):
        os.remove(self.path)


def runtests(options):
    os.environ['DJANGO_SETTINGS_MODULE'] = options.settings

    conf = load_settings(options.settings)

    if conf is None:
        sys.stderr.write('Cannot load settings module: %s\n' % options.settings)
        return sys.exit(1)

    settings.configure(**conf)

    redis_conf_path = options.conf or join(dirname(__file__), 'tests', 'redis.conf')

    server.configure(options.server_path, redis_conf_path, 0)

    try:
        redis_conf_template = open(join(dirname(__file__), 'tests' ,'redis.conf.tpl')).read()
    except OSError, IOError:
        sys.stderr.write('Cannot find template for redis.conf.\n')
    context = Context({
        'redis_socket': join(dirname(abspath(__file__)), 'tests', 'redis.sock')
    })

    contents = Template(redis_conf_template).render(context)

    with TmpFile(redis_conf_path, contents):
        with server:
            from django.test.simple import DjangoTestSuiteRunner
            runner = DjangoTestSuiteRunner(verbosity=options.verbosity, interactive=True, failfast=False)
            failures = runner.run_tests(['testapp'])

    sys.exit(failures)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-s", "--server", dest="server_path", action="store",
        type="string", default=None, help="Path to the redis server executable")
    parser.add_option("-c", "--conf", dest="conf", default=None,
        help="Path to the redis configuration file.")
    parser.add_option("-v", "--verbosity", dest="verbosity", default=1, type="int",
        help="Change the verbostiy of the redis-server.")
    parser.add_option("--settings", dest="settings", default="tests.settings",
        help="Django settings module to use for the tests.")

    (options, args) = parser.parse_args()

    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)

    runtests(options)
