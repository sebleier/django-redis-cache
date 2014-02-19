==========================
Redis Django Cache Backend
==========================

A simple Redis cache backend for Django


Changelog
=========

0.11.1
------

* Allows user to specify the connection pool class kwargs, e.g. timeout,
    max_connections, etc.

0.11.0
------

* Adds support for specifying the connection pool class.
* Adds ability to set the max connections for the connection pool.

0.10.0
------

Adds Support for Python 3.3 and Django 1.5 and 1.6.  Huge thanks to Carl Meyer
for his work.

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

Notes
-----

This cache backend requires the `redis-py`_ Python client library for
communicating with the Redis server.

Redis writes to disk asynchronously so there is a slight chance
of losing some data, but for most purposes this is acceptable.

In order to use ``redis.connection.HiredisParser`` parser class, you need to
pip install `hiredis`_.  This is the recommended parser class.

Usage
-----

1. Run ``python setup.py install`` to install,
   or place ``redis_cache`` on your Python path.

2. Modify your Django settings to use ``redis_cache`` :

On Django < 1.3::

    CACHE_BACKEND = 'redis_cache.cache://<host>:<port>'

On Django >= 1.3::


    # When using TCP connections
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': '<host>:<port>',
            'OPTIONS': {
                'DB': 1,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 50,
                    'timeout': 20,
                }
                'MAX_CONNECTIONS': 1000,
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
                'PARSER_CLASS': 'redis.connection.HiredisParser'
            },
        },
    }

.. _redis-py: http://github.com/andymccurdy/redis-py/
.. _hiredis: https://github.com/pietern/hiredis-py

