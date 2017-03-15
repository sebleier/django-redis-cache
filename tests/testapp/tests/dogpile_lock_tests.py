# -*- coding: utf-8 -*-
import Queue
import sys
import threading
import time

from django.test import TestCase, override_settings

from tests.testapp.tests.base_tests import SetupMixin

LOCATION = "127.0.0.1:6381"


class GetOrSetThread(threading.Thread):
    """Thread class using get_or_set, for testing locks behavior."""
    def __init__(self, cache, get_or_set_args, exceptions, assertValue, _raise=False):
        super(GetOrSetThread, self).__init__()
        self.cache = cache
        self._get_or_set_args = get_or_set_args
        self._exceptions = exceptions
        self._assertValue = assertValue

    def run(self):
        key, func, timeout = self._get_or_set_args
        try:
            value = self.cache.get_or_set(key, func, timeout)
            self._assertValue(value)
        except Exception:
            self._exceptions.put(sys.exc_info())

    @staticmethod
    def raise_thread_exceptions(exception_queue):
        while True:
            try:
                exc_info = exception_queue.get(block=False)
            except Queue.Empty:
                break
            else:
                exc_type, exc_obj, exc_trace = exc_info
                raise exc_type, exc_obj, exc_trace


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': LOCATION,
            'OPTIONS': {
                'DB': 15,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'PICKLE_VERSION': -1,
                'DOGPILE_LOCK_TIMEOUT': 1,
            },
        },
    }
)
class DogpileLockTestCase(SetupMixin, TestCase):

    def test_get_or_set_dogpile_lock(self):
        self.reset_pool()
        cache = self.get_cache()

        num_calls = {'count': 0}
        num_calls_lock = threading.RLock()
        thread_exceptions = Queue.Queue()

        def get_locked_expensive_function():
            execution_lock = threading.Lock()
            execution_lock.acquire()
            def expensive_function():
                with num_calls_lock:
                    num_calls['count'] += 1
                execution_lock.acquire()
                return 42
            return expensive_function, execution_lock.release

        self.assertEqual(num_calls['count'], 0)
        expensive_function1, release1 = get_locked_expensive_function()
        expensive_function2, release2 = get_locked_expensive_function()
        expensive_function3, release3 = get_locked_expensive_function()
        expensive_function4, release4 = get_locked_expensive_function()
        thread1 = GetOrSetThread(
            self.cache, ('test_get_or_set_dogpile_lock', expensive_function1, 1),
            thread_exceptions, lambda x: self.assertEqual(x, 42),
        )
        thread1.start()
        time.sleep(.1)  # Make sure the thread code is executed
        self.assertEqual(num_calls['count'], 1)
        thread2 = GetOrSetThread(
            self.cache, ('test_get_or_set_dogpile_lock', expensive_function2, 1),
            thread_exceptions, lambda x: self.assertEqual(x, None),
        )
        thread2.start()
        thread2.join(1.)
        GetOrSetThread.raise_thread_exceptions(thread_exceptions)
        # Dogpile lock should have prevented the code execution
        self.assertEqual(num_calls['count'], 1)
        release1()
        # Now finishing the thread1
        thread1.join(1.)
        GetOrSetThread.raise_thread_exceptions(thread_exceptions)

        # Dogpile has been released, should execute again
        thread3 = GetOrSetThread(
            self.cache, ('test_get_or_set_dogpile_lock', expensive_function3, 1),
            thread_exceptions, lambda x: self.assertEqual(x, 42),
        )
        thread3.start()
        release3()
        GetOrSetThread.raise_thread_exceptions(thread_exceptions)
        ## Value cached, nothing to hold for
        self.assertEqual(num_calls['count'], 1)

        time.sleep(1.)

        # should now be expired
        thread4 = GetOrSetThread(
            self.cache, ('test_get_or_set_dogpile_lock', expensive_function4, 1),
            thread_exceptions, lambda x: self.assertEqual(x, 42),
        )
        thread4.start()
        release4()
        thread4.join(1.)
        GetOrSetThread.raise_thread_exceptions(thread_exceptions)
        self.assertEqual(num_calls['count'], 2)

    def test_get_or_set_dogpile_deadlock(self):
        self.reset_pool()
        cache = self.get_cache()

        class ExpireFailed(Exception):
            """Expiration failed."""

        def expire_failure(*args, **kwargs):
            raise ExpireFailed('Expire failed.')

        num_calls = {'count': 0}
        num_calls_lock = threading.RLock()
        thread_exceptions = Queue.Queue()

        def get_locked_expensive_function():
            execution_lock = threading.Lock()
            execution_lock.acquire()
            def expensive_function():
                with num_calls_lock:
                    num_calls['count'] += 1
                execution_lock.acquire()
                return 42
            return expensive_function, execution_lock.release

        expensive_function1, release1 = get_locked_expensive_function()
        expensive_function2, release2 = get_locked_expensive_function()
        expensive_function3, release3 = get_locked_expensive_function()
        expensive_function4, release4 = get_locked_expensive_function()

        # Patch expire to generate an expiration failure
        expires = {}
        for client in cache.clients.values():
            expires[client] = client.expire
            client.expire = expire_failure

        try:

            self.assertEqual(num_calls['count'], 0)
            thread1 = GetOrSetThread(
                self.cache, ('test_get_or_set_dogpile_deadlock', expensive_function1, 1),
                thread_exceptions, lambda x: self.assertEqual(x, 42),
            )
            thread1.start()
            time.sleep(.1)  # Make sure the thread code is executed
            self.assertEqual(num_calls['count'], 1)
            thread2 = GetOrSetThread(
                self.cache, ('test_get_or_set_dogpile_deadlock', expensive_function2, 1),
                thread_exceptions, lambda x: self.assertEqual(x, None),
            )
            thread2.start()
            thread2.join(1.)
            GetOrSetThread.raise_thread_exceptions(thread_exceptions)
            # Dogpile lock should have prevented the code execution
            self.assertEqual(num_calls['count'], 1)
            # Now finishing the thread1
            release1()
            thread1.join(1.)
            with self.assertRaises(ExpireFailed):
                GetOrSetThread.raise_thread_exceptions(thread_exceptions)
        finally:
            # expiration works again
            for client in cache.clients.values():
                client.expire = expires[client]

        # Dogpile has not been released because of failure, should execute again
        thread3 = GetOrSetThread(
            self.cache, ('test_get_or_set_dogpile_deadlock', expensive_function3, 1),
            thread_exceptions, lambda x: self.assertEqual(x, None),
        )
        thread3.start()
        thread3.join(1.)
        GetOrSetThread.raise_thread_exceptions(thread_exceptions)
        self.assertEqual(num_calls['count'], 1)

        time.sleep(2.)

        # Now the dogpile lock should be expired
        thread4 = GetOrSetThread(
            self.cache, ('test_get_or_set_dogpile_deadlock', expensive_function4, 1),
            thread_exceptions, lambda x: self.assertEqual(x, 42),
        )
        thread4.start()
        release4()
        thread4.join(1.)
        GetOrSetThread.raise_thread_exceptions(thread_exceptions)
        self.assertEqual(num_calls['count'], 2)
