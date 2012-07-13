from .base_settings import *


CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': [
            '127.0.0.1:6380',
            '127.0.0.1:6381',
            '127.0.0.1:6382',
        ],
        'OPTIONS': {
            'DB': 15,
            'PASSWORD': 'yadayada',
            'PARSER_CLASS': 'redis.connection.PythonParser',
            'PICKLE_VERSION': 2,
        },
    },
}
