from django.core.cache import get_cache, cache
from django.http import HttpResponse
#test with django 1.3.1 by feifan 2/14/2012

def someview(request):
    #cachex = get_cache('redis_cache.cache://127.0.0.1')
    cache.set("foo", "bar")
    cache2 = get_cache('2ndcache')
    cache2.set('foo', 'bar2') #shold use db 14, not overwirte foo in default db15

    return HttpResponse("should be bar and bar2 in next line:<br>%s %s" % (cache.get('foo'), cache2.get('foo')))
