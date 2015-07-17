import sys
import django


PY3 = (sys.version_info >= (3,))

try:
    # Django 1.5+
    from django.utils.encoding import smart_text, smart_bytes
except ImportError:
    # older Django, thus definitely Python 2
    from django.utils.encoding import smart_unicode, smart_str
    smart_text = smart_unicode
    smart_bytes = smart_str

if PY3:
    bytes_type = bytes
    from urllib.parse import parse_qs, urlparse
else:
    bytes_type = str
    from urlparse import parse_qs, urlparse


if django.VERSION[:2] >= (1, 6):
    from django.core.cache.backends.base import DEFAULT_TIMEOUT as DJANGO_DEFAULT_TIMEOUT
    DEFAULT_TIMEOUT = DJANGO_DEFAULT_TIMEOUT
else:
    DEFAULT_TIMEOUT = None


def python_2_unicode_compatible(klass):
    """
    A decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.

    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.

    Backported from Django 1.5+.
    """
    if not PY3:
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
    return klass
