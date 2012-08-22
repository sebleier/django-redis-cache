==========================
Redis Django Cache Backend
==========================

A Redis cache backend for Django


Changelog
=========

1.0.0
-----

* Deprecate support for django < 1.3 and redis < 2.4.  If you need support for those versions,
    pin django-redis-cache to a version less than 1.0, i.e. pip install django-redis-cache<1.0
* Application level sharding when a list of locations is provided in the settings.
* Delete keys using wildcard syntax.
* Clear cache using version to delete only keys under that namespace.
* Ability to select pickle protocol version.
* Support for Master-Slave setup


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
            'LOCATIONS': [
                '<host>:<port>',
                '<host>:<port>',
                '<host>:<port>',
            ],
            'OPTIONS': {
                'DB': 1,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': 2,
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
                'PICKLE_VERSION': 2,
            },
        },
    }

    # For Master-Slave Setup, specify the host:port of the master
    # redis-server instance.
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATIONS': [
                '<host>:<port>',
                '<host>:<port>',
                '<host>:<port>',
            ],
            'OPTIONS': {
                'DB': 1,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': 2,
                'MASTER_CACHE': '<master host>:<master port>',
            },
        },
    }



Usage
=====

django-redis-cache shares the same API as django's built-in cache backends,
with a few exceptions.

``cache.delete_pattern``

Delete keys using glob-style pattern.

example::

    >>> from news.models import Story
    >>>
    >>> most_viewed = Story.objects.most_viewed()
    >>> highest_rated = Story.objects.highest_rated()
    >>> cache.set('news.stories.most_viewed', most_viewed)
    >>> cache.set('news.stories.highest_rated', highest_rated)
    >>> data = cache.get_many(['news.stories.highest_rated', 'news.stories.most_viewed'])
    >>> len(data)
    2
    >>> cache.delete_pattern('news.stores.*')
    >>> data = cache.get_many(['news.stories.highest_rated', 'news.stories.most_viewed'])
    >>> len(data)
    0

``cache.clear``

Same as django's ``cache.clear``, except that you can optionally specify a
version and all keys with that version will be deleted.  If no version is
provided, all keys are flushed from the cache.

``cache.reinsert_keys``

This helper method retrieves all keys and inserts them back into the cache.  This
is useful when changing the pickle protocol number of all the cache entries.
As of django-redis-cache < 1.0, all cache entries were pickled using version 0.
To reduce the memory footprint of the redis-server, simply run this method to
upgrade cache entries to the latest protocol.

Running Tests
=============

Currently, running tests requires installing my fork of redis-py (https://github.com/sebleier/redis-py)

./run_tests -s path/to/redis-server


.. _redis-py: http://github.com/andymccurdy/redis-py/
.. _redis: http://github.com/antirez/redis/
.. _hiredis: http://github.com/antirez/hiredis/
.. _python: http://python.org