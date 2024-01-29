from setuptools import setup

setup(
    name="django-redis-cache",
    url="http://github.com/sebleier/django-redis-cache/",
    author="Sean Bleier",
    author_email="sebleier@gmail.com",
    version="3.0.1",
    license="BSD",
    packages=["redis_cache", "redis_cache.backends"],
    description="Redis Cache Backend for Django",
    install_requires=['redis<4.0'],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.2",
    ],
)
