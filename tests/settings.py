DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = [
    'tests.testapp',
]

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '192.168.32.139:6379',
        'OPTIONS': { # optional
            'DB': 15,
            #'PASSWORD': 'yadayada',
        },
    },
    '2ndcache': { #test under django 1.3+
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '192.168.32.139:6379',
        'OPTIONS': { # optional
            'DB': 14,
            #'PASSWORD': 'yadayada',
        },
    },
}

ROOT_URLCONF = 'tests.urls'
