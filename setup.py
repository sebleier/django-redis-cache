from setuptools import setup

setup(
    name = "django-redis-cache",
    url = "http://github.com/sebleier/django-redis-cache/",
    author = "Sean Bleier",
    author_email = "sebleier@gmail.com",
    version = "0.11.0",
    packages = ["redis_cache"],
    description = "Redis Cache Backend for Django",
    install_requires=['redis>=2.4.5',],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Environment :: Web Environment",
        "Framework :: Django",
    ],
)
