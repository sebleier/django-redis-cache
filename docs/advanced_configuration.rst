Advanced Configuration
**********************

Example Setting
---------------

.. code:: python

    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': '127.0.0.1:6379',
            'OPTIONS': {
                'DB': 1,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
                'PICKLE_VERSION': -1,
            },
        },
    }

Pluggable Backends
------------------

django-redis-cache comes with a couple pluggable backends, one for a unified
keyspace and one for a sharded keyspace. The former can be in the form of a
single redis server or several redis servers setup in a primary/secondary
configuration. The primary is used for writing and secondaries are
replicated versions of the primary for read-access.

**Default Backend:** ``redis_cache.RedisCache``

.. code:: python

    # Unified keyspace
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            ...
        }
    }

    # Sharded keyspace
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.ShardedRedisCache',
            ...
        }
    }


Location Schemes
----------------

The ``LOCATION`` contains the information for the redis server's location,
which can be the address/port or the server path to the unix domain socket. The
location can be a single string or a list of strings.  Several schemes for
defining the location can be used.  Here is a list of example schemes:

    * ``127.0.0.1:6379``

    * ``/path/to/socket``

    * ``redis://[:password]@localhost:6379/0``

    * ``rediss://[:password]@localhost:6379/0``

    * ``unix://[:password]@/path/to/socket.sock?db=0``


Database Number
---------------

The ``DB`` option will allow key/values to exist in a different keyspace.  The
``DB`` value can either be defined in the ``OPTIONS`` or in the ``LOCATION``
scheme. Note that in the default config of redis, you have only 16 databases and the valid values are from 0 to 15.

**Default DB:** ``1``

.. code:: python

    CACHES = {
        'default': {
            'OPTIONS': {
                'DB': 1,
                ..
            },
            ...
        }
    }


Password
--------

If the redis server is password protected, you can specify the ``PASSWORD``
option.

.. code:: python

    CACHES = {
        'default': {
            'OPTIONS': {
                'PASSWORD': 'yadayada',
                ...
            },
            ...
        }
    }


Master/Slave Setup
------------------

It's possible to have multiple redis servers in a master/slave or
primary/secondary configuration.  Here we have the primary server acting as a
read/write server and secondary servers as read-only.

.. code:: python

    CACHES = {
        'default': {
            'LOCATION': [
                '127.0.0.1:6379',  # Primary
                '127.0.0.1:6380',  # Secondary
                '127.0.0.1:6381',  # Secondary
            ],
            'OPTIONS': {
                'PASSWORD': 'yadayada',
                'MASTER_CACHE': '127.0.0.1:6379',
                ...
            },
            ...
        }
    }




Pluggable Parser Classes
------------------------

`redis-py`_ comes with two parsers: ``HiredisParser`` and ``PythonParser``.
The former uses the `hiredis`_ library to parse responses from the redis
server, while the latter uses Python.  Hiredis is a library that uses C, so it
is much faster than the python parser, but requires installing the library
separately.

**Default Parser:** ``redis.connection.PythonParser``

The default parser is the Python parser because there is no other dependency,
but I would recommend using `hiredis`_:

    ``pip install hiredis``


.. code:: python

    CACHES = {
        'default': {
            'OPTIONS': {
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                ...
            },
            ...
        }
    }


Pickle Version
--------------

When using the pickle serializer, you can use ``PICKLE_VERSION`` to specify
the protocol version of pickle you want to use to serialize your python objects.

**Default Pickle Version:** `-1`

The default pickle protocol is -1, which is the highest and latest version.
This value should be pinned to a specific protocol number, since ``-1`` means
different things between versions of Python.

.. code:: python

    CACHES = {
        'default': {
            'OPTIONS': {
                'PICKLE_VERSION': 2,
                ...
            },
            ...
        },
    }


Socket Timeout and Socket Create Timeout
----------------------------------------

When working with a TCP connection, it may be beneficial to set the
``SOCKET_TIMEOUT`` and ``SOCKET_CONNECT_TIMEOUT`` options to prevent your
app from blocking indefinitely.

If provided, the socket will time out when the established connection exceeds
``SOCKET_TIMEOUT`` seconds.

Similarly, the socket will time out if it takes more than
``SOCKET_CONNECT_TIMEOUT`` seconds to establish.

**Default Socket Timeout:** ``None``

**Default Socket Connect Timeout:** ``None``

.. code:: python

    CACHES={
        'default': {
            'OPTIONS': {
                'SOCKET_TIMEOUT': 5,
                'SOCKET_CONNECT_TIMEOUT': 5,
                ...
            }
            ...
        }
    }


Connection Pool
---------------

There is an associated overhead when creating connections to a redis server.
Therefore, it's beneficial to create a pool of connections that the cache can
reuse to send or retrieve data from the redis server.

``CONNECTION_POOL_CLASS`` can be used to specify a class to use for the
connection pool.  In addition, you can provide custom keyword arguments using
the ``CONNECTION_POOL_CLASS_KWARGS`` option that will be passed into the class
when it's initialized.

**Default Connection Pool:** ``redis.ConnectionPool``

.. code:: python

    CACHES = {
        'default': {
            'OPTIONS': {
                'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 50,
                    'timeout': 20,
                    ...
                },
                ...
            },
            ...
        }
    }


Pluggable Serializers
---------------------

You can use ``SERIALIZER_CLASS`` to specify a class that will
serialize/deserialize data.  In addition, you can provide custom keyword
arguments using the ``SERIALIZER_CLASS_KWARGS`` option that will be passed into
the class when it's initialized.

The default serializer in django-redis-cache is the pickle serializer. It can
serialize most python objects, but is slow and not always safe.  Also included
are serializer using json, msgpack, and yaml. Not all serializers can handle
Python objects, so they are limited to primitive data types.


**Default Serializer:** ``redis_cache.serializers.PickleSerializer``

.. code:: python

    CACHES = {
        'default': {
            'OPTIONS': {
                'SERIALIZER_CLASS': 'redis_cache.serializers.PickleSerializer',
                'SERIALIZER_CLASS_KWARGS': {
                    'pickle_version': -1
                },
                ...
            },
            ...
        }
    }


Pluggable Compressors
---------------------

You can use ``COMPRESSOR_CLASS`` to specify a class that will
compress/decompress data.  Use the ``COMPRESSOR_CLASS_KWARGS`` option to
initialize the compressor class.

The default compressor is ``NoopCompressor`` which does not compress your data.
However, if you want to compress your data, you can use one of the included
compressor classes:


**Default Compressor:** ``redis_cache.compressors.NoopCompressor``

.. code:: python

    # zlib compressor
    CACHES = {
        'default': {
            'OPTIONS': {
                'COMPRESSOR_CLASS': 'redis_cache.compressors.ZLibCompressor',
                'COMPRESSOR_CLASS_KWARGS': {
                    'level': 5,  # 0 - 9; 0 - no compression; 1 - fastest, biggest; 9 - slowest, smallest
                },
                ...
            },
            ...
        }
    }

    # bzip2 compressor
    CACHES = {
        'default': {
            'OPTIONS': {
                'COMPRESSOR_CLASS': 'redis_cache.compressors.BZip2Compressor',
                'COMPRESSOR_CLASS_KWARGS': {
                    'compresslevel': 5,  # 1 - 9; 1 - fastest, biggest; 9 - slowest, smallest
                },
                ...
            },
            ...
        }
    }


.. _redis-py: http://github.com/andymccurdy/redis-py/
.. _hiredis: https://pypi.python.org/pypi/hiredis/
