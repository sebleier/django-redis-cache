Intro and Quick Start
*********************

Intro
=====

`django-redis-cache`_ is a cache backend for the `Django`_ web framework.  It
uses the `redis`_ server, which is a in-memory key-value data structure server.
Similar to the great `Memcached`_ in performance, it has several features that
makes it more appealing.

    * Multiple data structures types, e.g. string, list, set, sorted sets, and hashes.

    * Atomic pipelines: guaranteed that multiple commands will run sequentially and uninterrupted.

    * Pub/Sub: subscribe to a channel and listen for messages from other processes.

    * Can back data to disk, which can keep a cache warm even if the process is killed.

    * Lua scripting

    * Clustering (as of 3.0)

    * Many more.

Many of these features are irrelevant to caching, but can be used by other
areas of a web stack and therefore offers a compelling case to simplify your
infrastructure.



Quick Start
===========


**Recommended:**

* `redis`_ >= 2.8

* `redis-py`_ >= 3.0.0

* `python`_ >= 2.7


1. Install `redis`_.  You can use ``install_redis.sh`` to install a local copy
of redis.  Start the server by running ``./src/redis-server``

2. Run ``pip install django-redis-cache``.

3. Modify your Django settings to use ``redis_cache``.

.. code:: python

    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': 'localhost:6379',
        },
    }

**Warning: By default, django-redis-cache set keys in the database 1 of Redis. By default, a session with redis-cli start on database 0. Switch to database 1 with** ``SELECT 1``.

.. _Django: https://www.djangoproject.com/
.. _django-redis-cache: http://github.com/sebleier/django-redis-cache
.. _redis-py: http://github.com/andymccurdy/redis-py/
.. _redis: http://github.com/antirez/redis/
.. _python: http://python.org
.. _Memcached: http://memcached.org
