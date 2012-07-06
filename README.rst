==========================
Redis Django Cache Backend
==========================

A Redis cache backend for Django


Changelog
=========

1.0.0
-----

* Deprecate support for django < 1.3 and redis < 2.4.  If you need support for those versions,
    pin django-redis-cache to a version less than 1.0.
* Client-side sharding when multiple locations provided.
* Delete keys using wildcard syntax.
* Clear cache using version to delete only keys under that namespace.
* Ability to select pickle version.


0.9.0
-----

Redis cache now allows you to use either a TCP connection or Unix domain
socket to connect to your redis server.  Using a TCP connection is useful for
when you have your redis server separate from your app server and/or within
a distributed environment.  Unix domain sockets are useful if you have your
redis server and application running on the same machine and want the fastest
possible connection.

You can now specify (optionally) what parser class you want redis-py to use
when parsing messages from the redis server.  redis-py will pick the best
parser for you implicitly, but using the ``PARSER_CLASS`` setting gives you
control and the option to roll your own parser class if you are so bold.


Requirements
============

`redis-py`_ >= 2.4.5
`redis`_ >= 2.4
`hiredis`_
`python`_ >= 2.5


Installation
============

pip install django-redis-cache
or
python setup.py install


Configuraton
============

example::
    # When using TCP connections
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': [
                '<host>:<port>',
                '<host>:<port>',
                '<host>:<port>',
            ],
            'OPTIONS': {
                'DB': 1,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': 2, # Defaults to 0
            },
        },
    }

    # When using unix domain sockets
    # Note: ``LOCATION`` needs to be the same as the ``unixsocket`` setting
    # in your redis.conf
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': '/path/to/socket/file',
            'OPTIONS': {
                'DB': 1,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': 2, # Defaults to 0
            },
        },
    }


Running Tests
=============

Currently, running tests requires installing my fork of redis-py (https://github.com/sebleier/redis-py)

./run_tests -s path/to/redis-server


.. _redis-py: http://github.com/andymccurdy/redis-py/
.. _redis: http://github.com/antirez/redis/
.. _hiredis: http://github.com/antirez/hiredis/
.. _python: http://python.org