#!/usr/bin/env python
# cardinal_pythonlib/dogpile_cache.py

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

# noinspection PyPackageRequirements
from dogpile.cache import make_region
# from dogpile.util import compat  # repr used as the default instead of compat.to_str  # noqa

TESTING_VERBOSE = True
TESTING_USE_PRETTY_LOGS = True  # False to make this standalone
if TESTING_USE_PRETTY_LOGS:
    from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

DEBUG_INTERNALS = False

log = logging.getLogger(__name__)  # don't use BraceStyleAdapter; {} used
log.addHandler(logging.NullHandler())


# =============================================================================
# Helper functions
# =============================================================================

def repr_parameter(param: inspect.Parameter) -> str:
    """
    Provides a ``repr``-style representation of a function parameter.
    """
    return (
        "Parameter(name={name}, annotation={annotation}, kind={kind}, "
        "default={default}".format(
            name=param.name, annotation=param.annotation, kind=param.kind,
            default=param.default)
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
        extra="|{}".format(namespace) if namespace is not None else "",
    )


# =============================================================================
# New function key generators
# =============================================================================

def fkg_allowing_type_hints(
        namespace: Optional[str],
        fn: Callable,
        to_str: Callable[[Any], str] = repr) -> Callable[[Any], str]:
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
    argnames = [p.name for p in sig.parameters.values()
                if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
    has_self = bool(argnames and argnames[0] in ('self', 'cls'))

    def generate_key(*args: Any, **kw: Any) -> str:
        """
        Makes the actual key for a specific call to the decorated function,
        with particular ``args``/``kwargs``.
        """
        if kw:
            raise ValueError("This dogpile.cache key function generator, "
                             "fkg_allowing_type_hints, "
                             "does not accept keyword arguments.")
        if has_self:
            # Unlike dogpile's default, make it instance- (or class-) specific
            # by including a representation of the "self" or "cls" argument:
            args = [hex(id(args[0]))] + list(args[1:])
        key = namespace + "|" + " ".join(map(to_str, args))
        if DEBUG_INTERNALS:
            log.debug("fkg_allowing_type_hints.generate_key() -> " + repr(key))
        return key

    return generate_key


def multikey_fkg_allowing_type_hints(
        namespace: Optional[str],
        fn: Callable,
        to_str: Callable[[Any], str] = repr) -> Callable[[Any], List[str]]:
    """
    Equivalent of :func:`dogpile.cache.util.function_multi_key_generator`, but
    using :func:`inspect.signature` instead.

    Also modified to make the cached function unique per INSTANCE for normal
    methods of a class.
    """

    namespace = get_namespace(fn, namespace)

    sig = inspect.signature(fn)
    argnames = [p.name for p in sig.parameters.values()
                if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
    has_self = bool(argnames and argnames[0] in ('self', 'cls'))

    def generate_keys(*args: Any, **kw: Any) -> List[str]:
        if kw:
            raise ValueError("This dogpile.cache key function generator, "
                             "multikey_fkg_allowing_type_hints, "
                             "does not accept keyword arguments.")
        if has_self:
            # Unlike dogpile's default, make it instance- (or class-) specific
            # by including a representation of the "self" or "cls" argument:
            args = [hex(id(args[0]))] + list(args[1:])
        keys = [namespace + "|" + key for key in map(to_str, args)]
        if DEBUG_INTERNALS:
            log.debug("multikey_fkg_allowing_type_hints.generate_keys() -> " +
                      repr(keys))
        return keys

    return generate_keys


def kw_fkg_allowing_type_hints(
        namespace: Optional[str],
        fn: Callable,
        to_str: Callable[[Any], str] = repr) -> Callable[[Any], str]:
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
    argnames = [p.name for p in parameters
                if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
    has_self = bool(argnames and argnames[0] in ('self', 'cls'))

    if DEBUG_INTERNALS:
        log.debug(
            "At start of kw_fkg_allowing_type_hints: namespace={namespace},"
            "parameters=[{parameters}], argnames={argnames}, "
            "has_self={has_self}, fn={fn}".format(
                namespace=namespace,
                parameters=", ".join(repr_parameter(p) for p in parameters),
                argnames=repr(argnames),
                has_self=has_self,
                fn=repr(fn),
            ))

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
            as_kwargs['*args'] = loose_args
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
        argument_values = ["{k}={v}".format(k=key, v=to_str(as_kwargs[key]))
                           for key in sorted(as_kwargs.keys())]
        key = namespace + '|' + " ".join(argument_values)
        if DEBUG_INTERNALS:
            log.debug("kw_fkg_allowing_type_hints.generate_key() -> " +
                      repr(key))
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


# =============================================================================
# Unit tests
# =============================================================================

def unit_test_cache() -> None:
    mycache = make_region()
    mycache.configure(backend='dogpile.cache.memory')

    plain_fkg = fkg_allowing_type_hints
    kw_fkg = kw_fkg_allowing_type_hints
    # I'm not sure what dogpile.cache.utils.function_multi_key_generator is
    # used for, so haven't fully tested multikey_fkg_allowing_type_hints, but
    # it works internally in the same way as fkg_allowing_type_hints.

    fn_was_called = False

    def test(result: str, should_call_fn: bool, reset: bool = True) -> None:
        nonlocal fn_was_called
        log.info(result)
        assert fn_was_called == should_call_fn, (
            "fn_was_called={}, should_call_fn={}".format(
                fn_was_called, should_call_fn))
        if reset:
            fn_was_called = False

    def fn_called(text: str) -> None:
        log.info(text)
        nonlocal fn_was_called
        fn_was_called = True

    @mycache.cache_on_arguments(function_key_generator=None)
    def no_params_dogpile_default_fkg():  # no type hints!
        fn_called("CACHED FUNCTION no_params_dogpile_default_fkg() CALLED")
        return "no_params_dogpile_default_fkg: hello"

    @mycache.cache_on_arguments(function_key_generator=plain_fkg)
    def noparams() -> str:
        fn_called("CACHED FUNCTION noparams() CALLED")
        return "noparams: hello"

    @mycache.cache_on_arguments(function_key_generator=plain_fkg)
    def oneparam(a: str) -> str:
        fn_called("CACHED FUNCTION oneparam() CALLED")
        return "oneparam: hello, " + a

    @mycache.cache_on_arguments(function_key_generator=plain_fkg)
    def twoparam_with_default_wrong_dec(a: str, b: str = "Zelda") -> str:
        fn_called("CACHED FUNCTION twoparam_with_default_wrong_dec() CALLED")
        return ("twoparam_with_default_wrong_dec: hello, " + a +
                "; this is " + b)

    @mycache.cache_on_arguments(function_key_generator=kw_fkg)
    def twoparam_with_default_right_dec(a: str, b: str = "Zelda") -> str:
        fn_called("CACHED FUNCTION twoparam_with_default_right_dec() CALLED")
        return ("twoparam_with_default_right_dec: hello, " + a +
                "; this is " + b)

    @mycache.cache_on_arguments(function_key_generator=kw_fkg)
    def twoparam_all_defaults_no_typehints(a="David", b="Zelda"):
        fn_called("CACHED FUNCTION twoparam_all_defaults_no_typehints() "
                  "CALLED")
        return ("twoparam_all_defaults_no_typehints: hello, " + a +
                "; this is " + b)

    @mycache.cache_on_arguments(function_key_generator=kw_fkg)
    def fn_args_kwargs(*args, **kwargs):
        fn_called("CACHED FUNCTION fn_args_kwargs() CALLED")
        return ("fn_args_kwargs: args={}, kwargs={}".format(repr(args),
                                                            repr(kwargs)))

    @mycache.cache_on_arguments(function_key_generator=kw_fkg)
    def fn_all_possible(a, b, *args, d="David", **kwargs):
        fn_called("CACHED FUNCTION fn_all_possible() CALLED")
        return "fn_all_possible: a={}, b={}, args={}, d={}, kwargs={}".format(
            repr(a), repr(b), repr(args), repr(d), repr(kwargs))

    class TestClass(object):
        c = 999

        def __init__(self, a: int = 200) -> None:
            self.a = a

        @mycache.cache_on_arguments(function_key_generator=None)
        def no_params_dogpile_default_fkg(self):  # no type hints!
            fn_called("CACHED FUNCTION TestClass."
                      "no_params_dogpile_default_fkg() CALLED")
            return "TestClass.no_params_dogpile_default_fkg: hello"

        @mycache.cache_on_arguments(function_key_generator=None)
        def dogpile_default_test_2(self):  # no type hints!
            fn_called("CACHED FUNCTION TestClass."
                      "dogpile_default_test_2() CALLED")
            return "TestClass.dogpile_default_test_2: hello"

        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def noparams(self) -> str:
            fn_called("CACHED FUNCTION TestClass.noparams() CALLED")
            return "Testclass.noparams: hello; a={}".format(self.a)

        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def no_params_instance_cache(self) -> str:
            fn_called("PER-INSTANCE-CACHED FUNCTION "
                      "TestClass.no_params_instance_cache() CALLED")
            return "TestClass.no_params_instance_cache: a={}".format(self.a)

        # Decorator order is critical here:
        # https://stackoverflow.com/questions/1987919/why-can-decorator-not-decorate-a-staticmethod-or-a-classmethod  # noqa
        @classmethod
        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def classy(cls) -> str:
            fn_called("CACHED FUNCTION TestClass.classy() CALLED")
            return "TestClass.classy: hello; c={}".format(cls.c)

        @staticmethod
        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def static() -> str:
            fn_called("CACHED FUNCTION TestClass.static() CALLED")
            return "TestClass.static: hello"

        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def oneparam(self, q: str) -> str:
            fn_called("CACHED FUNCTION TestClass.oneparam() CALLED")
            return "TestClass.oneparam: hello, " + q

        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def fn_all_possible(self, a, b, *args, d="David", **kwargs):
            fn_called("CACHED FUNCTION TestClass.fn_all_possible() CALLED")
            return ("TestClass.fn_all_possible: a={}, b={}, args={}, d={}, "
                    "kwargs={}".format(repr(a), repr(b), repr(args), repr(d),
                                       repr(kwargs)))

        @property
        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def prop(self) -> str:
            fn_called("CACHED PROPERTY TestClass.prop() CALLED")
            return "TestClass.prop: a={}".format(repr(self.a))

    class SecondTestClass:
        def __init__(self) -> None:
            self.d = 5

        @mycache.cache_on_arguments(function_key_generator=None)
        def dogpile_default_test_2(self):  # no type hints!
            fn_called("CACHED FUNCTION SecondTestClass."
                      "dogpile_default_test_2() CALLED")
            return "SecondTestClass.dogpile_default_test_2: hello"

    class Inherited(TestClass):
        def __init__(self, a=101010):
            super().__init__(a=a)

        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def noparams(self) -> str:
            fn_called("CACHED FUNCTION Inherited.noparams() CALLED")
            return "Inherited.noparams: hello; a={}".format(self.a)

        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def no_params_instance_cache(self) -> str:
            fn_called("PER-INSTANCE-CACHED FUNCTION "
                      "Inherited.no_params_instance_cache() CALLED")
            return "Inherited.no_params_instance_cache: a={}".format(self.a)

        # Decorator order is critical here:
        # https://stackoverflow.com/questions/1987919/why-can-decorator-not-decorate-a-staticmethod-or-a-classmethod  # noqa
        @classmethod
        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def classy(cls) -> str:
            fn_called("CACHED FUNCTION Inherited.classy() CALLED")
            return "Inherited.classy: hello; c={}".format(cls.c)

        @staticmethod
        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def static() -> str:
            fn_called("CACHED FUNCTION Inherited.static() CALLED")
            return "Inherited.static: hello"

        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def oneparam(self, q: str) -> str:
            fn_called("CACHED FUNCTION Inherited.oneparam() CALLED")
            return "Inherited.oneparam: hello, " + q

        # BUT fn_all_possible IS NOT OVERRIDDEN

        @property
        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def prop(self) -> str:
            fn_called("CACHED PROPERTY Inherited.prop() CALLED")
            return "Inherited.prop: a={}".format(repr(self.a))

    log.warning("Fetching cached information #1 (should call noparams())...")
    test(noparams(), True)
    log.warning("Fetching cached information #2 (should not call noparams())...")  # noqa
    test(noparams(), False)

    log.warning("Testing functions with other signatures...")
    test(oneparam("Arthur"), True)
    test(oneparam("Arthur"), False)
    test(oneparam("Bob"), True)
    test(oneparam("Bob"), False)
    test(twoparam_with_default_wrong_dec("Celia"), True)
    test(twoparam_with_default_wrong_dec("Celia"), False)
    test(twoparam_with_default_wrong_dec("Celia", "Yorick"), True)
    test(twoparam_with_default_wrong_dec("Celia", "Yorick"), False)

    log.warning("Trying with keyword arguments and wrong key generator")
    try:
        log.info(twoparam_with_default_wrong_dec(a="Celia", b="Yorick"))
        raise AssertionError("Inappropriate success with keyword arguments!")
    except ValueError:
        log.info("Correct rejection of keyword arguments")

    log.warning("Trying with keyword arguments and right key generator")
    test(twoparam_with_default_right_dec(a="Celia"), True)
    test(twoparam_with_default_right_dec(a="Celia", b="Yorick"), True)
    test(twoparam_with_default_right_dec(b="Yorick", a="Celia"), False)
    test(twoparam_with_default_right_dec("Celia", b="Yorick"), False)

    test(twoparam_all_defaults_no_typehints(), True)
    test(twoparam_all_defaults_no_typehints(a="Edith"), True)
    test(twoparam_all_defaults_no_typehints(a="Edith"), False)
    test(twoparam_all_defaults_no_typehints(b="Romeo"), True)
    test(twoparam_all_defaults_no_typehints(b="Romeo"), False)
    test(twoparam_all_defaults_no_typehints("Greta", b="Romeo"), True)
    test(twoparam_all_defaults_no_typehints("Greta", b="Romeo"), False)
    test(twoparam_all_defaults_no_typehints(a="Felicity", b="Sigurd"), True)
    test(twoparam_all_defaults_no_typehints(a="Felicity", b="Sigurd"), False)
    test(twoparam_all_defaults_no_typehints("Felicity", "Sigurd"), False)
    test(twoparam_all_defaults_no_typehints("Felicity", "Sigurd"), False)
    test(twoparam_all_defaults_no_typehints(b="Sigurd", a="Felicity"), False)
    test(twoparam_all_defaults_no_typehints(b="Sigurd", a="Felicity"), False)

    test(fn_args_kwargs(1, 2, 3, d="David", f="Edgar"), True)
    test(fn_args_kwargs(1, 2, 3, d="David", f="Edgar"), False)

    test(fn_args_kwargs(p="another", q="thing"), True)
    test(fn_args_kwargs(p="another", q="thing"), False)
    log.warning("The next call MUST NOT go via the cache, i.e. func should be CALLED")  # noqa
    test(fn_args_kwargs(p="another q=thing"), True)
    test(fn_args_kwargs(p="another q=thing"), False)

    test(fn_all_possible(10, 11, 12, "Horace", "Iris"), True)
    test(fn_all_possible(10, 11, 12, "Horace", "Iris"), False)
    test(fn_all_possible(10, 11, 12, d="Horace"), True)
    test(fn_all_possible(10, 11, 12, d="Horace"), False)
    test(fn_all_possible(98, 99, d="Horace"), True)
    test(fn_all_possible(98, 99, d="Horace"), False)
    test(fn_all_possible(98, 99, d="Horace", p="another", q="thing"), True)
    test(fn_all_possible(98, 99, d="Horace", p="another", q="thing"), False)
    test(fn_all_possible(98, 99, d="Horace", r="another", s="thing"), True)
    test(fn_all_possible(98, 99, d="Horace", r="another", s="thing"), False)

    log.warning("Testing class member functions")
    t = TestClass()
    test(t.noparams(), True)
    test(t.noparams(), False)
    test(t.classy(), True)
    test(t.classy(), False)
    test(t.static(), True)
    test(t.static(), False)
    test(t.oneparam("Arthur"), True)
    test(t.oneparam("Arthur"), False)
    test(t.oneparam("Bob"), True)
    test(t.oneparam("Bob"), False)
    test(t.fn_all_possible(10, 11, 12, "Horace", "Iris"), True)
    test(t.fn_all_possible(10, 11, 12, "Horace", "Iris"), False)
    test(t.fn_all_possible(10, 11, 12, d="Horace"), True)
    test(t.fn_all_possible(10, 11, 12, d="Horace"), False)
    test(t.fn_all_possible(98, 99, d="Horace"), True)
    test(t.fn_all_possible(98, 99, d="Horace"), False)
    test(t.fn_all_possible(98, 99, d="Horace", p="another", q="thing"), True)
    test(t.fn_all_possible(98, 99, d="Horace", p="another", q="thing"), False)
    test(t.fn_all_possible(98, 99, d="Horace", r="another", s="thing"), True)
    test(t.fn_all_possible(98, 99, d="Horace", r="another", s="thing"), False)
    test(t.prop, True)
    test(t.prop, False)

    log.warning("Testing functions for another INSTANCE of the same class")
    t_other = TestClass(a=999)
    test(t_other.noparams(), True)
    test(t_other.noparams(), False)
    test(t_other.classy(), False)  # SAME CLASS as t; shouldn't be re-called
    test(t_other.classy(), False)
    test(t_other.static(), False)  # SAME CLASS as t; shouldn't be re-called
    test(t_other.static(), False)
    test(t_other.oneparam("Arthur"), True)
    test(t_other.oneparam("Arthur"), False)
    test(t_other.oneparam("Bob"), True)
    test(t_other.oneparam("Bob"), False)
    test(t_other.fn_all_possible(10, 11, 12, "Horace", "Iris"), True)
    test(t_other.fn_all_possible(10, 11, 12, "Horace", "Iris"), False)
    test(t_other.fn_all_possible(10, 11, 12, d="Horace"), True)
    test(t_other.fn_all_possible(10, 11, 12, d="Horace"), False)
    test(t_other.fn_all_possible(98, 99, d="Horace"), True)
    test(t_other.fn_all_possible(98, 99, d="Horace"), False)
    test(t_other.fn_all_possible(98, 99, d="Horace", p="another", q="thing"), True)  # noqa
    test(t_other.fn_all_possible(98, 99, d="Horace", p="another", q="thing"), False)  # noqa
    test(t_other.fn_all_possible(98, 99, d="Horace", r="another", s="thing"), True)  # noqa
    test(t_other.fn_all_possible(98, 99, d="Horace", r="another", s="thing"), False)  # noqa
    test(t_other.prop, True)
    test(t_other.prop, False)

    test(t.no_params_instance_cache(), True)
    test(t.no_params_instance_cache(), False)
    test(t_other.no_params_instance_cache(), True)
    test(t_other.no_params_instance_cache(), False)

    log.warning("Testing functions for instance of a derived class")
    t_inh = Inherited(a=777)
    test(t_inh.noparams(), True)
    test(t_inh.noparams(), False)
    test(t_inh.classy(), True)
    test(t_inh.classy(), False)
    test(t_inh.static(), True)
    test(t_inh.static(), False)
    test(t_inh.oneparam("Arthur"), True)
    test(t_inh.oneparam("Arthur"), False)
    test(t_inh.oneparam("Bob"), True)
    test(t_inh.oneparam("Bob"), False)
    test(t_inh.fn_all_possible(10, 11, 12, "Horace", "Iris"), True)
    test(t_inh.fn_all_possible(10, 11, 12, "Horace", "Iris"), False)
    test(t_inh.fn_all_possible(10, 11, 12, d="Horace"), True)
    test(t_inh.fn_all_possible(10, 11, 12, d="Horace"), False)
    test(t_inh.fn_all_possible(98, 99, d="Horace"), True)
    test(t_inh.fn_all_possible(98, 99, d="Horace"), False)
    test(t_inh.fn_all_possible(98, 99, d="Horace", p="another", q="thing"), True)  # noqa
    test(t_inh.fn_all_possible(98, 99, d="Horace", p="another", q="thing"), False)  # noqa
    test(t_inh.fn_all_possible(98, 99, d="Horace", r="another", s="thing"), True)  # noqa
    test(t_inh.fn_all_possible(98, 99, d="Horace", r="another", s="thing"), False)  # noqa
    test(t_inh.prop, True)
    test(t_inh.prop, False)

    test(no_params_dogpile_default_fkg(), True)
    test(no_params_dogpile_default_fkg(), False)
    try:
        test(t.no_params_dogpile_default_fkg(), True)
        log.info("dogpile.cache default FKG correctly distinguishing between "
                 "plain and class-member function in same module")
    except AssertionError:
        log.warning("Known dogpile.cache default FKG problem - conflates "
                    "plain/class member function of same name (unless "
                    "namespace is manually given)")
    test(t.no_params_dogpile_default_fkg(), False)

    t2 = SecondTestClass()
    test(t.dogpile_default_test_2(), True)
    test(t.dogpile_default_test_2(), False)
    try:
        test(t2.dogpile_default_test_2(), True)
        log.info("dogpile.cache default FKG correctly distinguishing between "
                 "member functions of two different classes with same name")
    except AssertionError:
        log.warning("Known dogpile.cache default FKG problem - conflates "
                    "member functions of two different classes where "
                    "functions have same name (unless namespace is manually "
                    "given)")
    test(t2.dogpile_default_test_2(), False)

    log.info("Success!")


# TEST THIS WITH:
# python -m cardinal_pythonlib.dogpile_cache
if __name__ == '__main__':
    level = logging.DEBUG if TESTING_VERBOSE else logging.INFO
    if TESTING_USE_PRETTY_LOGS:
        main_only_quicksetup_rootlogger(level=level)
    else:
        logging.basicConfig(level=level)
    unit_test_cache()
