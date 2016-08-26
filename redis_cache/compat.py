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
