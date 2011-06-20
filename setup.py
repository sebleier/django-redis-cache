from distutils.core import setup

setup(
    name = "django-redis-cache",
    url = "http://github.com/sebleier/django-redis-cache/",
    author = "Sean Bleier",
    author_email = "sebleier@gmail.com",
    version = "0.5.1",
    packages = ["redis_cache"],
    description = "Redis Cache Backend for Django",
    install_requires=['redis>=2.4.4',],
    classifiers = [
        "Programming Language :: Python",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Environment :: Web Environment",
        "Framework :: Django",
    ],
)
