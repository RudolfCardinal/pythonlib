#!/usr/bin/env python
# cardinal_pythonlib/django/request_cache.py

"""
===============================================================================

    Original code copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Implement a request cache for Django.**

"""

# http://stackoverflow.com/questions/3151469/per-request-cache-in-django

from threading import currentThread

from django.core.cache.backends.locmem import LocMemCache

_request_cache = {}
_installed_middleware = False


def get_request_cache():
    """
    Returns the Django request cache for the current thread.
    Requires that ``RequestCacheMiddleware`` is loaded.
    """
    assert _installed_middleware, 'RequestCacheMiddleware not loaded'
    return _request_cache[currentThread()]


# LocMemCache is a threadsafe local memory cache
class RequestCache(LocMemCache):
    """
    Local memory request cache for Django.
    """
    def __init__(self):
        name = 'locmemcache@%i' % hash(currentThread())
        params = dict()
        super(RequestCache, self).__init__(name, params)


class RequestCacheMiddleware(object):
    """
    Django middleware to implement a request cache.
    """
    def __init__(self):
        global _installed_middleware
        _installed_middleware = True

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def process_request(self, request):
        cache = _request_cache.get(currentThread()) or RequestCache()
        _request_cache[currentThread()] = cache

        cache.clear()
