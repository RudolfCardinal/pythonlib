#!/usr/bin/env python
# cardinal_pythonlib/dogpile_cache.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Extensions to dogpile.cache.**

1.  The basic cache objects.

2.  FIX FOR DOGPILE.CACHE FOR DECORATED FUNCTIONS, 2017-07-28 (PLUS SOME OTHER
    IMPROVEMENTS). SEE

        https://bitbucket.org/zzzeek/dogpile.cache/issues/96/error-in-python-35-with-use-of-deprecated

    This fixes a crash using type-hinted functions under Python 3.5 with
    ``dogpile.cache==0.6.4``:

    .. code-block:: none

        Traceback (most recent call last):
          File "/usr/lib/python3.5/runpy.py", line 184, in _run_module_as_main
            "__main__", mod_spec)
          File "/usr/lib/python3.5/runpy.py", line 85, in _run_code
            exec(code, run_globals)
          File "/home/rudolf/Documents/code/camcops/server/camcops_server/cc_modules/cc_cache.py", line 64, in <module>
            unit_test_cache()
          File "/home/rudolf/Documents/code/camcops/server/camcops_server/cc_modules/cc_cache.py", line 50, in unit_test_cache
            def testfunc() -> str:
          File "/home/rudolf/dev/venvs/camcops/lib/python3.5/site-packages/dogpile/cache/region.py", line 1215, in decorator
            key_generator = function_key_generator(namespace, fn)
          File "/home/rudolf/dev/venvs/camcops/lib/python3.5/site-packages/dogpile/cache/util.py", line 31, in function_key_generator
            args = inspect.getargspec(fn)
          File "/usr/lib/python3.5/inspect.py", line 1045, in getargspec
            raise ValueError("Function has keyword-only arguments or annotations"
        ValueError: Function has keyword-only arguments or annotations, use getfullargspec() API which can support them

3.  Other improvements include:

    - the cache decorators operate as:
        - PER-INSTANCE caches for class instances, provided the first parameter
          is named "self";
        - PER-CLASS caches for classmethods, provided the first parameter is
          named "cls";
        - PER-FUNCTION caches for staticmethods and plain functions

    - keyword arguments are supported

    - properties are supported (the @property decorator must be ABOVE the
      cache decorator)

    - Note that this sort of cache relies on the generation of a STRING KEY
      from the function arguments. It uses the ``hex(id())`` function for
      ``self``/``cls`` arguments, and the ``to_str()`` function, passed as a
      parameter, for others (for which the default is ``"repr"``; see
      discussion below as to why ``"repr"`` is suitable while ``"str"`` is
      not).

"""  # noqa


# =============================================================================
# Imports; logging
# =============================================================================

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEBUG_INTERNALS = True


# =============================================================================
# Helper functions
# =============================================================================


def repr_parameter(param: inspect.Parameter) -> str:
    """
    Provides a ``repr``-style representation of a function parameter.
    """
    return (
        f"Parameter(name={param.name}, annotation={param.annotation}, "
        f"kind={param.kind}, default={param.default}"
    )


def get_namespace(fn: Callable, namespace: Optional[str]) -> str:
    """
    Returns a representation of a function's name (perhaps within a namespace),
    like

    .. code-block:: none

        mymodule:MyClass.myclassfunc  # with no namespace
        mymodule:MyClass.myclassfunc|somenamespace  # with a namespace

    Args:
        fn: a function
        namespace: an optional namespace, which can be of any type but is
            normally a ``str``; if not ``None``, ``str(namespace)`` will be
            added to the result. See
            https://dogpilecache.readthedocs.io/en/latest/api.html#dogpile.cache.region.CacheRegion.cache_on_arguments
    """  # noqa
    # See hidden attributes with dir(fn)
    # noinspection PyUnresolvedReferences
    return "{module}:{name}{extra}".format(
        module=fn.__module__,
        name=fn.__qualname__,  # __qualname__ includes class name, if present
        extra=f"|{namespace}" if namespace is not None else "",
    )


# =============================================================================
# New function key generators
# =============================================================================


def fkg_allowing_type_hints(
    namespace: Optional[str], fn: Callable, to_str: Callable[[Any], str] = repr
) -> Callable[[Any], str]:
    """
    Replacement for :func:`dogpile.cache.util.function_key_generator` that
    handles type-hinted functions like

    .. code-block:: python

        def testfunc(param: str) -> str:
            return param + "hello"

    ... at which :func:`inspect.getargspec` balks; plus
    :func:`inspect.getargspec` is deprecated in Python 3.

    Used as an argument to e.g. ``@cache_region_static.cache_on_arguments()``.

    Also modified to make the cached function unique per INSTANCE for normal
    methods of a class.

    Args:
        namespace: optional namespace, as per :func:`get_namespace`
        fn: function to generate a key for (usually the function being
            decorated)
        to_str: function to apply to map arguments to a string (to make a
            unique key for a particular call to the function); by default it
            is :func:`repr`

    Returns:
        a function that generates a string key, based on a given function as
        well as arguments to the returned function itself.
    """

    namespace = get_namespace(fn, namespace)

    sig = inspect.signature(fn)
    argnames = [
        p.name
        for p in sig.parameters.values()
        if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    ]
    has_self = bool(argnames and argnames[0] in ("self", "cls"))

    def generate_key(*args: Any, **kw: Any) -> str:
        """
        Makes the actual key for a specific call to the decorated function,
        with particular ``args``/``kwargs``.
        """
        if kw:
            raise ValueError(
                "This dogpile.cache key function generator, "
                "fkg_allowing_type_hints, "
                "does not accept keyword arguments."
            )
        if has_self:
            # Unlike dogpile's default, make it instance- (or class-) specific
            # by including a representation of the "self" or "cls" argument:
            args = [hex(id(args[0]))] + list(args[1:])
        key = namespace + "|" + " ".join(map(to_str, args))
        if DEBUG_INTERNALS:
            log.debug(
                f"fkg_allowing_type_hints.generate_key("
                f"args={args!r}, kw={kw!r}); argnames = {argnames!r} "
                f"-> {key!r}"
            )
        return key

    return generate_key


def multikey_fkg_allowing_type_hints(
    namespace: Optional[str], fn: Callable, to_str: Callable[[Any], str] = repr
) -> Callable[[Any], List[str]]:
    """
    Equivalent of :func:`dogpile.cache.util.function_multi_key_generator`, but
    using :func:`inspect.signature` instead.

    Also modified to make the cached function unique per INSTANCE for normal
    methods of a class.
    """

    namespace = get_namespace(fn, namespace)

    sig = inspect.signature(fn)
    argnames = [
        p.name
        for p in sig.parameters.values()
        if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    ]
    has_self = bool(argnames and argnames[0] in ("self", "cls"))

    def generate_keys(*args: Any, **kw: Any) -> List[str]:
        if kw:
            raise ValueError(
                "This dogpile.cache key function generator, "
                "multikey_fkg_allowing_type_hints, "
                "does not accept keyword arguments."
            )
        if has_self:
            # Unlike dogpile's default, make it instance- (or class-) specific
            # by including a representation of the "self" or "cls" argument:
            args = [hex(id(args[0]))] + list(args[1:])
        keys = [namespace + "|" + key for key in map(to_str, args)]
        if DEBUG_INTERNALS:
            log.debug(
                f"multikey_fkg_allowing_type_hints.generate_keys() -> {keys!r}"
            )
        return keys

    return generate_keys


def kw_fkg_allowing_type_hints(
    namespace: Optional[str], fn: Callable, to_str: Callable[[Any], str] = repr
) -> Callable[[Any], str]:
    """
    As for :func:`fkg_allowing_type_hints`, but allowing keyword arguments.

    For ``kwargs`` passed in, we will build a ``dict`` of all argname (key) to
    argvalue (values) pairs, including default args from the argspec, and then
    alphabetize the list before generating the key.

    NOTE ALSO that once we have keyword arguments, we should be using
    :func:`repr`, because we need to distinguish

    .. code-block:: python

        kwargs = {'p': 'another', 'q': 'thing'}
        # ... which compat.string_type will make into
        #         p=another q=thing
        # ... from
        kwargs = {'p': 'another q=thing'}

    Also modified to make the cached function unique per INSTANCE for normal
    methods of a class.
    """

    namespace = get_namespace(fn, namespace)

    sig = inspect.signature(fn)
    parameters = list(sig.parameters.values())  # convert from odict_values
    argnames = [
        p.name
        for p in parameters
        if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    ]
    has_self = bool(argnames and argnames[0] in ("self", "cls"))

    if DEBUG_INTERNALS:
        param_str = ", ".join(repr_parameter(p) for p in parameters)
        log.debug(
            f"At start of kw_fkg_allowing_type_hints: namespace={namespace},"
            f"parameters=[{param_str}], argnames={argnames!r}, "
            f"has_self={has_self}, fn={fn!r}"
        )

    def generate_key(*args: Any, **kwargs: Any) -> str:
        as_kwargs = {}  # type: Dict[str, Any]
        loose_args = []  # type: List[Any]  # those captured by *args
        # 1. args: get the name as well.
        for idx, arg in enumerate(args):
            if idx >= len(argnames):
                # positional argument to be scooped up with *args
                loose_args.append(arg)
            else:
                # normal plain positional argument
                if has_self and idx == 0:  # "self" or "cls" initial argument
                    argvalue = hex(id(arg))
                else:
                    argvalue = arg
                as_kwargs[argnames[idx]] = argvalue
        # 1b. args with no name
        if loose_args:
            as_kwargs["*args"] = loose_args
            # '*args' is guaranteed not to be a parameter name in its own right
        # 2. kwargs
        as_kwargs.update(kwargs)
        # 3. default values
        for param in parameters:
            if param.default != inspect.Parameter.empty:
                if param.name not in as_kwargs:
                    as_kwargs[param.name] = param.default
        # 4. sorted by name
        #    ... but also incorporating the name of the argument, because once
        #    we allow the arbitrary **kwargs format, order is no longer
        #    sufficient to discriminate
        #       fn(p="another", q="thing")
        #    from
        #       fn(r="another", s="thing")
        argument_values = [
            "{k}={v}".format(k=key, v=to_str(as_kwargs[key]))
            for key in sorted(as_kwargs.keys())
        ]
        key = namespace + "|" + " ".join(argument_values)
        if DEBUG_INTERNALS:
            log.debug(f"kw_fkg_allowing_type_hints.generate_key() -> {key!r}")
        return key

    return generate_key


# =============================================================================
# Default function key generator with a short name
# =============================================================================

fkg = kw_fkg_allowing_type_hints

# Can now do:
#
# @mycache.cache_on_arguments(function_key_generator=fkg)
# def myfunc():
#     pass
