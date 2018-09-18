#!/usr/bin/env python
# cardinal_pythonlib/django/function_cache.py

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

**Cache the results of function calls using Django.**

Based on https://github.com/rchrd2/django-cache-decorator
but fixed for Python 3 / Django 1.10.

"""

import hashlib
import logging
from typing import Any, Callable, Dict, Tuple

from django.core.cache import cache  # default cache

from cardinal_pythonlib.json.serialize import json_encode

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

FunctionType = Callable[..., Any]
ArgsType = Tuple[Any, ...]
KwargsType = Dict[str, Any]


def get_call_signature(fn: FunctionType,
                       args: ArgsType,
                       kwargs: KwargsType,
                       debug_cache: bool = False) -> str:
    """
    Takes a function and its args/kwargs, and produces a string description
    of the function call (the call signature) suitable for use indirectly as a
    cache key. The string is a JSON representation. See ``make_cache_key`` for
    a more suitable actual cache key.
    """
    # Note that the function won't have the __self__ argument (as in
    # fn.__self__), at this point, even if it's a member function.
    try:
        call_sig = json_encode((fn.__qualname__, args, kwargs))
    except TypeError:
        log.critical(
            "\nTo decorate using @django_cache_function without specifying "
            "cache_key, the decorated function's owning class and its "
            "parameters must be JSON-serializable (see jsonfunc.py, "
            "django_cache_fn.py).\n")
        raise
    if debug_cache:
        log.debug("Making call signature {}".format(repr(call_sig)))
    return call_sig


def make_cache_key(call_signature: str,
                   debug_cache: bool = False) -> str:
    """
    Takes a function and its args/kwargs, and produces a string description
    of the function call (the call signature) suitable for use as a cache key.
    The string is an MD5 hash of the JSON-encoded call signature.
    The logic behind these decisions is as follows:

    - We have a bunch of components of arbitrary type, and we need to get
      a unique string out.
    - We shouldn't use ``str()``, because that is often poorly specified; e.g.
      is ``'a.b.c'`` a ``TableId``, or is it a ``ColumnId`` with no ``'db'``
      field?
    - We could use ``repr()``: sometimes that gives us helpful things that
      could in principle be passed to ``eval()``, in which case ``repr()`` would
      be fine, but sometimes it doesn't, and gives unhelpful things like
      ``'<__main__.Thing object at 0x7ff3093ebda0>'``.
    - However, if something encodes to JSON, that representation should
      be reversible and thus contain the right sort of information.
    - Note also that bound methods will come with a ``self`` argument, for
      which the address may be very relevant...
    - Let's go with ``repr()``. Users of the cache decorator should not pass
      objects whose ``repr()`` includes the memory address of the object unless
      they want those objects to be treated as distinct.
    - Ah, no. The cache itself will pickle and unpickle things, and this
      will change memory addresses of objects. So we can't store a reference
      to an object using ``repr()`` and using ``cache.add()``/``pickle()`` and
      hope they'll come out the same.
    - Use the JSON after all.
    - And do it in ``get_call_signature()``, not here.
    - That means that any class we wish to decorate WITHOUT specifying a
      cache key manually must support JSON.
    """
    key = hashlib.md5(call_signature.encode("utf-8")).hexdigest()
    if debug_cache:
        log.debug("Making cache key {} from call_signature {}".format(
            key, repr(call_signature)))
    return key


def django_cache_function(timeout: int = 5 * 60,
                          cache_key: str = '',
                          debug_cache: bool = False):
    """
    Decorator to add caching to a function in Django.
    Uses the Django default cache.

    Args:

        timeout: timeout in seconds; use None for "never expire", as 0 means
            "do not cache".

        cache_key: optional cache key to use (if falsy, we'll invent one)
        debug_cache: show hits/misses?
    """
    cache_key = cache_key or None

    def decorator(fn):
        def wrapper(*args, **kwargs):
            # - NOTE that Django returns None from cache.get() for "not in
            #   cache", so can't cache a None value;
            #   https://docs.djangoproject.com/en/1.10/topics/cache/#basic-usage  # noqa
            # - We need to store a bit more than just the function result
            #   anyway, to detect hash collisions when the user doesn't specify
            #   the cache_key, so we may as well use that format even if the
            #   user does specify the cache_key, and then we can store a None
            #   result properly as well.
            if cache_key:
                # User specified a cache key. This is easy.
                call_sig = ''
                _cache_key = cache_key
                check_stored_call_sig = False
            else:
                # User didn't specify a cache key, so we'll do one
                # automatically. Since we do this via a hash, there is a small
                # but non-zero chance of a hash collision.
                call_sig = get_call_signature(fn, args, kwargs)
                _cache_key = make_cache_key(call_sig)
                check_stored_call_sig = True
            if debug_cache:
                log.critical("Checking cache for key: " + _cache_key)
            cache_result_tuple = cache.get(_cache_key)  # TALKS TO CACHE HERE
            if cache_result_tuple is None:
                if debug_cache:
                    log.debug("Cache miss")
            else:
                if debug_cache:
                    log.debug("Cache hit")
                cached_call_sig, func_result = cache_result_tuple
                if (not check_stored_call_sig) or cached_call_sig == call_sig:
                    return func_result
                log.warning(
                    "... Cache hit was due to hash collision; cached_call_sig "
                    "{} != call_sig {}".format(
                        repr(cached_call_sig), repr(call_sig)))
                # If we get here, either it wasn't in the cache, or something
                # was in the cache that matched by cache_key but was actually a
                # hash collision. Either way, we must do the real work.
            func_result = fn(*args, **kwargs)
            cache_result_tuple = (call_sig, func_result)
            cache.set(key=_cache_key, value=cache_result_tuple,
                      timeout=timeout)  # TALKS TO CACHE HERE
            return func_result

        return wrapper

    return decorator
