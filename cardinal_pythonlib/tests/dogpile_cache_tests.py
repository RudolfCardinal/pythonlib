#!/usr/bin/env python
# cardinal_pythonlib/tests/dogpile_cache_tests.py

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

**Unit tests.**

"""


# =============================================================================
# Imports; logging
# =============================================================================

import logging
import unittest

# noinspection PyPackageRequirements
from dogpile.cache import make_region

from cardinal_pythonlib.dogpile_cache import (
    fkg_allowing_type_hints,
    kw_fkg_allowing_type_hints,
)

log = logging.getLogger(__name__)


# =============================================================================
# Some testing for args/kwargs!
# =============================================================================

_TEST_PYTHON_ARGS_KWARGS_BEHAVIOUR = """

These test functions seems consistent across Python 3.6-3.10:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
from typing import Any

def f1(*args, **kwargs):
    print(f"f1: args={args!r}, kwargs={kwargs!r}")

def f2(*args: Any, **kwargs: Any) -> None:
    print(f"f2: args={args!r}, kwargs={kwargs!r}")

def decorated(fn):
    def intermediate_fn(*args, **kwargs):
        print(f"intermediate_fn: args={args!r}, kwargs={kwargs!r}")
        return fn(*args, **kwargs)
    return intermediate_fn

@decorated
def f3(a, b):
    print(f"f3: a={a!r}, b={b!r}")

@decorated
def f4(a, b = "b_default"):
    print(f"f3: a={a!r}, b={b!r}")

print(sys.version)
print("--- Both as named args:")
f1(a="a", b="b")
f2(a="a", b="b")
f3(a="a", b="b")
f4(a="a", b="b")
print("--- Both as positional args:")
f1("a", "b")
f2("a", "b")
f3("a", "b")
f4("a", "b")
print("--- a positional, b named:")
f1("a", b="b")
f2("a", b="b")
f3("a", b="b")
f4("a", b="b")

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python 3.6 gives:

    3.6.15 (default, Apr 25 2022, 01:55:53)
    [GCC 9.4.0]
    --- Both as named args:
    f1: args=(), kwargs={'a': 'a', 'b': 'b'}
    --- Both as positional args:
    f1: args=('a', 'b'), kwargs={}
    --- a positional, b named:
    f1: args=('a',), kwargs={'b': 'b'}

    # ... others not yet checked

Python 3.8 gives:

    3.8.5 (default, Jul 20 2020, 23:11:29)
    [GCC 9.3.0]
    --- Both as named args:
    f1: args=(), kwargs={'a': 'a', 'b': 'b'}
    --- Both as positional args:
    f1: args=('a', 'b'), kwargs={}
    --- a positional, b named:
    f1: args=('a',), kwargs={'b': 'b'}

    # ... others not yet checked

Python 3.10 gives:

    3.10.6 (main, Mar 10 2023, 10:55:28) [GCC 11.3.0]
    --- Both as named args:
    f1: args=(), kwargs={'a': 'a', 'b': 'b'}
    f2: args=(), kwargs={'a': 'a', 'b': 'b'}
    intermediate_fn: args=(), kwargs={'a': 'a', 'b': 'b'}
    f3: a='a', b='b'
    intermediate_fn: args=(), kwargs={'a': 'a', 'b': 'b'}
    f3: a='a', b='b'
    --- Both as positional args:
    f1: args=('a', 'b'), kwargs={}
    f2: args=('a', 'b'), kwargs={}
    intermediate_fn: args=('a', 'b'), kwargs={}
    f3: a='a', b='b'
    intermediate_fn: args=('a', 'b'), kwargs={}
    f3: a='a', b='b'
    --- a positional, b named:
    f1: args=('a',), kwargs={'b': 'b'}
    f2: args=('a',), kwargs={'b': 'b'}
    intermediate_fn: args=('a',), kwargs={'b': 'b'}
    f3: a='a', b='b'
    intermediate_fn: args=('a',), kwargs={'b': 'b'}
    f3: a='a', b='b'

So the type hints don't change it, and nor does the presence of a simple
decorator function.

"""

# =============================================================================
# Unit tests
# =============================================================================


class DogpileCacheTests(unittest.TestCase):
    @staticmethod
    def test_dogpile_cache() -> None:
        """
        Test our extensions to dogpile.cache.
        """

        # ---------------------------------------------------------------------
        # Testing framework
        # ---------------------------------------------------------------------

        mycache = make_region()
        mycache.configure(backend="dogpile.cache.memory")

        plain_fkg = fkg_allowing_type_hints
        kw_fkg = kw_fkg_allowing_type_hints
        # I'm not sure what dogpile.cache.utils.function_multi_key_generator is
        # used for, so haven't fully tested multikey_fkg_allowing_type_hints,
        # but it works internally in the same way as fkg_allowing_type_hints.

        # This variable gets serially altered in an inelegant way:
        fn_was_called = False

        def test(
            result: str, should_call_fn: bool, reset: bool = True
        ) -> None:
            """
            Typical use:

            .. code-block:: python

                @mycache.cache_on_arguments()
                def f(x):
                    return x

                test(f("x"), should_call_fn=True)  # called the first time
                test(f("x"), should_call_fn=False)  # not called the second

            Here, we:

            - receive the result of the function, either because it's
              just been called, or because the cache provided the value;
            - report that result;
            - assume that the function itself would have called fn_called(),
              which would have set fn_was_called = True;
            - see if fn_was_called matches our expectation, and raise
              AssertionError otherwise;
            - reset fn_was_called to False, for subsequent testing, unless the
              caller asked us not to.
            """
            nonlocal fn_was_called
            log.info(result)
            assert fn_was_called == should_call_fn, (
                f"fn_was_called={fn_was_called}, "
                f"should_call_fn={should_call_fn}"
            )
            if reset:
                fn_was_called = False

        def fn_called(text: str) -> None:
            """
            Reports and marks that the function we are (inelegantly) monitoring
            has been called. (Called by a variety of test functions.)
            """
            log.info(text)
            nonlocal fn_was_called
            fn_was_called = True

        # ---------------------------------------------------------------------
        # Some plain functions with cache decorators
        # ---------------------------------------------------------------------

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

        # @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        # def twoparam_with_default_wrong_dec(a: str, b: str = "Zelda") -> str:
        #     # The decorator shouldn't work with keyword arguments.
        #     fn_called(
        #         "CACHED FUNCTION twoparam_with_default_wrong_dec() CALLED"
        #     )
        #     return (
        #         "twoparam_with_default_wrong_dec: hello, "
        #         + a
        #         + "; this is "
        #         + b
        #     )

        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def twoparam_with_default_right_dec(a: str, b: str = "Zelda") -> str:
            fn_called(
                "CACHED FUNCTION twoparam_with_default_right_dec() CALLED"
            )
            return (
                "twoparam_with_default_right_dec: hello, "
                + a
                + "; this is "
                + b
            )

        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def twoparam_all_defaults_no_typehints(a="David", b="Zelda"):
            fn_called(
                "CACHED FUNCTION twoparam_all_defaults_no_typehints() "
                "CALLED"
            )
            return (
                "twoparam_all_defaults_no_typehints: hello, "
                + a
                + "; this is "
                + b
            )

        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def arg_kwarg_wrong_dec(a: str, **kwargs: str) -> str:
            b = kwargs.get("b", "Yorick")  # default value
            fn_called("CACHED FUNCTION arg_kwarg_wrong_dec() CALLED")
            return "arg_kwarg_wrong_dec: hello, " + a + "; this is " + b

        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def arg_kwarg_right_dec(a: str, **kwargs: str) -> str:
            b = kwargs.get("b", "Yorick")  # default value
            fn_called("CACHED FUNCTION arg_kwarg_right_dec() CALLED")
            return "arg_kwarg_right_dec: hello, " + a + "; this is " + b

        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def fn_args_kwargs(*args, **kwargs):
            fn_called("CACHED FUNCTION fn_args_kwargs() CALLED")
            return f"fn_args_kwargs: args={args!r}, kwargs={kwargs!r}"

        @mycache.cache_on_arguments(function_key_generator=kw_fkg)
        def fn_all_possible(a, b, *args, d="David", **kwargs):
            fn_called("CACHED FUNCTION fn_all_possible() CALLED")
            return (
                f"fn_all_possible: a={a!r}, b={b!r}, args={args!r}, d={d!r}, "
                f"kwargs={kwargs!r}"
            )

        # ---------------------------------------------------------------------
        # Some classes with cache-decorated member functions
        # ---------------------------------------------------------------------

        class TestClass(object):
            c = 999

            def __init__(self, a: int = 200) -> None:
                self.a = a

            @mycache.cache_on_arguments(function_key_generator=None)
            def no_params_dogpile_default_fkg(self):  # no type hints!
                fn_called(
                    "CACHED FUNCTION TestClass."
                    "no_params_dogpile_default_fkg() CALLED"
                )
                return "TestClass.no_params_dogpile_default_fkg: hello"

            @mycache.cache_on_arguments(function_key_generator=None)
            def dogpile_default_test_2(self):  # no type hints!
                fn_called(
                    "CACHED FUNCTION TestClass."
                    "dogpile_default_test_2() CALLED"
                )
                return "TestClass.dogpile_default_test_2: hello"

            @mycache.cache_on_arguments(function_key_generator=plain_fkg)
            def noparams(self) -> str:
                fn_called("CACHED FUNCTION TestClass.noparams() CALLED")
                return f"Testclass.noparams: hello; a={self.a}"

            @mycache.cache_on_arguments(function_key_generator=kw_fkg)
            def no_params_instance_cache(self) -> str:
                fn_called(
                    "PER-INSTANCE-CACHED FUNCTION "
                    "TestClass.no_params_instance_cache() CALLED"
                )
                return f"TestClass.no_params_instance_cache: a={self.a}"

            # Decorator order is critical here:
            # https://stackoverflow.com/questions/1987919/why-can-decorator-not-decorate-a-staticmethod-or-a-classmethod  # noqa: E501
            @classmethod
            @mycache.cache_on_arguments(function_key_generator=plain_fkg)
            def classy(cls) -> str:
                fn_called("CACHED FUNCTION TestClass.classy() CALLED")
                return f"TestClass.classy: hello; c={cls.c}"

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
                return (
                    f"TestClass.fn_all_possible: a={a!r}, b={b!r}, "
                    f"args={args!r}, d={d!r}, kwargs={kwargs!r}"
                )

            @property
            @mycache.cache_on_arguments(function_key_generator=kw_fkg)
            def prop(self) -> str:
                fn_called("CACHED PROPERTY TestClass.prop() CALLED")
                return f"TestClass.prop: a={self.a!r}"

        class SecondTestClass:
            def __init__(self) -> None:
                self.d = 5

            @mycache.cache_on_arguments(function_key_generator=None)
            def dogpile_default_test_2(self):  # no type hints!
                fn_called(
                    "CACHED FUNCTION SecondTestClass."
                    "dogpile_default_test_2() CALLED"
                )
                return "SecondTestClass.dogpile_default_test_2: hello"

        class Inherited(TestClass):
            def __init__(self, a=101010):
                super().__init__(a=a)

            @mycache.cache_on_arguments(function_key_generator=plain_fkg)
            def noparams(self) -> str:
                fn_called("CACHED FUNCTION Inherited.noparams() CALLED")
                return f"Inherited.noparams: hello; a={self.a}"

            @mycache.cache_on_arguments(function_key_generator=kw_fkg)
            def no_params_instance_cache(self) -> str:
                fn_called(
                    "PER-INSTANCE-CACHED FUNCTION "
                    "Inherited.no_params_instance_cache() CALLED"
                )
                return f"Inherited.no_params_instance_cache: a={self.a}"

            # Decorator order is critical here:
            # https://stackoverflow.com/questions/1987919/why-can-decorator-not-decorate-a-staticmethod-or-a-classmethod  # noqa: E501
            @classmethod
            @mycache.cache_on_arguments(function_key_generator=plain_fkg)
            def classy(cls) -> str:
                fn_called("CACHED FUNCTION Inherited.classy() CALLED")
                return f"Inherited.classy: hello; c={cls.c}"

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
                return f"Inherited.prop: a={self.a!r}"

        # ---------------------------------------------------------------------
        # Perform the tests
        # ---------------------------------------------------------------------

        log.info("Fetching cached information #1 (should call noparams())...")
        test(noparams(), True)
        log.info(
            "Fetching cached information #2 (should not call noparams())..."
        )
        test(noparams(), False)

        log.info("Testing functions with other signatures...")
        test(oneparam("Arthur"), True)
        test(oneparam("Arthur"), False)
        test(oneparam("Bob"), True)
        test(oneparam("Bob"), False)

        # test(twoparam_with_default_wrong_dec("Celia"), True)
        # test(twoparam_with_default_wrong_dec("Celia"), False)
        # test(twoparam_with_default_wrong_dec("Celia", "Yorick"), True)
        # test(twoparam_with_default_wrong_dec("Celia", "Yorick"), False)

        # This test started to fail around Python 3.10 (or 3.8 sometimes?) and
        # it is likely to do with the version of dogpile.cache and/or
        # decorator. (For example: Python 3.10, dogpile.cache==0.9.2,
        # decorator=5.1.1 was failing here.)
        #
        # See https://github.com/RudolfCardinal/pythonlib/issues/15
        #
        # The problem was that if you explicitly called a function with keyword
        # syntax (named arguments), those parameters got moved into "args" if
        # they were also valid as positional arguments. The reason is that:
        #
        # - dogpile.cache.region.CacheRegion.cache_on_arguments decorates the
        #   cached function with decorator.decorate(); search for "return
        #   decorate".
        # - The kwsyntax flag is not specified, so it defaults to false.
        # - When kwsyntax is false, decorate() shufts things into args; see
        #   https://github.com/micheles/decorator/blob/master/docs/documentation.md#mimicking-the-behavior-of-functoolswrap
        #
        # It is not a change in Python behaviour (see
        # _TEST_PYTHON_ARGS_KWARGS_BEHAVIOUR above).
        #
        # But it is a slightly inappropriate test, because args are fine here
        # (functionally). Replaced with arg_kwarg_wrong_dec,
        # arg_kwarg_right_dec (below).
        #
        # log.info("Trying with keyword arguments and wrong key generator")
        # try:
        #     log.info(
        #         twoparam_with_default_wrong_dec(a="Celia[a]", b="Yorick[b]")
        #     )
        #     raise AssertionError(
        #         "Inappropriate success with keyword arguments!"
        #     )
        # except ValueError:
        #     log.info("Correct rejection of keyword arguments")

        log.info("Trying with keyword arguments and right key generator")
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
        test(
            twoparam_all_defaults_no_typehints(a="Felicity", b="Sigurd"), True
        )
        test(
            twoparam_all_defaults_no_typehints(a="Felicity", b="Sigurd"), False
        )
        test(twoparam_all_defaults_no_typehints("Felicity", "Sigurd"), False)
        test(twoparam_all_defaults_no_typehints("Felicity", "Sigurd"), False)
        test(
            twoparam_all_defaults_no_typehints(b="Sigurd", a="Felicity"), False
        )
        test(
            twoparam_all_defaults_no_typehints(b="Sigurd", a="Felicity"), False
        )

        log.info("Trying with keyword arguments and wrong key generator")
        try:
            log.info(arg_kwarg_wrong_dec(a="Celia[a]", b="Yorick[b]"))
            raise AssertionError(
                "Inappropriate success with keyword arguments!"
            )
        except ValueError:
            log.info("Correct rejection of keyword arguments")

        log.info("Trying with keyword arguments and right key generator")
        test(arg_kwarg_right_dec(a="Celia"), True)
        test(arg_kwarg_right_dec(a="Celia", b="Yorick"), True)
        test(arg_kwarg_right_dec(b="Yorick", a="Celia"), False)
        test(arg_kwarg_right_dec("Celia", b="Yorick"), False)

        test(fn_args_kwargs(1, 2, 3, d="David", f="Edgar"), True)
        test(fn_args_kwargs(1, 2, 3, d="David", f="Edgar"), False)

        test(fn_args_kwargs(p="another", q="thing"), True)
        test(fn_args_kwargs(p="another", q="thing"), False)
        log.info(
            "The next call MUST NOT go via the cache, "
            "i.e. func should be CALLED"
        )
        test(fn_args_kwargs(p="another q=thing"), True)
        test(fn_args_kwargs(p="another q=thing"), False)

        test(fn_all_possible(10, 11, 12, "Horace", "Iris"), True)
        test(fn_all_possible(10, 11, 12, "Horace", "Iris"), False)
        test(fn_all_possible(10, 11, 12, d="Horace"), True)
        test(fn_all_possible(10, 11, 12, d="Horace"), False)
        test(fn_all_possible(98, 99, d="Horace"), True)
        test(fn_all_possible(98, 99, d="Horace"), False)
        test(fn_all_possible(98, 99, d="Horace", p="another", q="thing"), True)
        test(
            fn_all_possible(98, 99, d="Horace", p="another", q="thing"), False
        )
        test(fn_all_possible(98, 99, d="Horace", r="another", s="thing"), True)
        test(
            fn_all_possible(98, 99, d="Horace", r="another", s="thing"), False
        )

        log.info("Testing class member functions")
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
        test(
            t.fn_all_possible(98, 99, d="Horace", p="another", q="thing"), True
        )
        test(
            t.fn_all_possible(98, 99, d="Horace", p="another", q="thing"),
            False,
        )
        test(
            t.fn_all_possible(98, 99, d="Horace", r="another", s="thing"), True
        )
        test(
            t.fn_all_possible(98, 99, d="Horace", r="another", s="thing"),
            False,
        )
        test(t.prop, True)
        test(t.prop, False)

        log.info("Testing functions for another INSTANCE of the same class")
        t_other = TestClass(a=999)
        test(t_other.noparams(), True)
        test(t_other.noparams(), False)
        test(
            t_other.classy(), False
        )  # SAME CLASS as t; shouldn't be re-called
        test(t_other.classy(), False)
        test(
            t_other.static(), False
        )  # SAME CLASS as t; shouldn't be re-called
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
        test(
            t_other.fn_all_possible(
                98, 99, d="Horace", p="another", q="thing"
            ),
            True,
        )
        test(
            t_other.fn_all_possible(
                98, 99, d="Horace", p="another", q="thing"
            ),
            False,
        )
        test(
            t_other.fn_all_possible(
                98, 99, d="Horace", r="another", s="thing"
            ),
            True,
        )
        test(
            t_other.fn_all_possible(
                98, 99, d="Horace", r="another", s="thing"
            ),
            False,
        )
        test(t_other.prop, True)
        test(t_other.prop, False)

        test(t.no_params_instance_cache(), True)
        test(t.no_params_instance_cache(), False)
        test(t_other.no_params_instance_cache(), True)
        test(t_other.no_params_instance_cache(), False)

        log.info("Testing functions for instance of a derived class")
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
        test(
            t_inh.fn_all_possible(98, 99, d="Horace", p="another", q="thing"),
            True,
        )
        test(
            t_inh.fn_all_possible(98, 99, d="Horace", p="another", q="thing"),
            False,
        )
        test(
            t_inh.fn_all_possible(98, 99, d="Horace", r="another", s="thing"),
            True,
        )
        test(
            t_inh.fn_all_possible(98, 99, d="Horace", r="another", s="thing"),
            False,
        )
        test(t_inh.prop, True)
        test(t_inh.prop, False)

        test(no_params_dogpile_default_fkg(), True)
        test(no_params_dogpile_default_fkg(), False)
        try:
            test(t.no_params_dogpile_default_fkg(), True)
            log.info(
                "dogpile.cache default FKG correctly distinguishing between "
                "plain and class-member function in same module"
            )
        except AssertionError:
            log.warning(
                "Known dogpile.cache default FKG problem - conflates "
                "plain/class member function of same name (unless "
                "namespace is manually given)"
            )
        test(t.no_params_dogpile_default_fkg(), False)

        t2 = SecondTestClass()
        test(t.dogpile_default_test_2(), True)
        test(t.dogpile_default_test_2(), False)
        try:
            test(t2.dogpile_default_test_2(), True)
            log.info(
                "dogpile.cache default FKG correctly distinguishing between "
                "member functions of two different classes with same name"
            )
        except AssertionError:
            log.warning(
                "Known dogpile.cache default FKG problem - conflates "
                "member functions of two different classes where "
                "functions have same name (unless namespace is manually "
                "given)"
            )
        test(t2.dogpile_default_test_2(), False)

        log.info("Success!")
