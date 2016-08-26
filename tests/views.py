from django.core.cache import caches
from django.http import HttpResponse


def someview(request):
    cache = caches['default']
    cache.set("foo", "bar")
    return HttpResponse("Pants")
