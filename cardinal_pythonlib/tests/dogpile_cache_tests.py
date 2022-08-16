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
import pytest

from cardinal_pythonlib.dogpile_cache import (
    fkg_allowing_type_hints,
    kw_fkg_allowing_type_hints,
)

log = logging.getLogger(__name__)


# =============================================================================
# Unit tests
# =============================================================================


class DogpileCacheTests(unittest.TestCase):
    @pytest.mark.xfail(reason="Needs investigating")
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
            assert (
                fn_was_called == should_call_fn
            ), f"fn_was_called={fn_was_called}, should_call_fn={should_call_fn}"
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

        @mycache.cache_on_arguments(function_key_generator=plain_fkg)
        def twoparam_with_default_wrong_dec(a: str, b: str = "Zelda") -> str:
            # The decorator shouldn't work with keyword arguments.
            fn_called(
                "CACHED FUNCTION twoparam_with_default_wrong_dec() CALLED"
            )
            return (
                "twoparam_with_default_wrong_dec: hello, "
                + a
                + "; this is "
                + b
            )

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
            # https://stackoverflow.com/questions/1987919/why-can-decorator-not-decorate-a-staticmethod-or-a-classmethod  # noqa
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
            # https://stackoverflow.com/questions/1987919/why-can-decorator-not-decorate-a-staticmethod-or-a-classmethod  # noqa
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
        test(twoparam_with_default_wrong_dec("Celia"), True)
        test(twoparam_with_default_wrong_dec("Celia"), False)
        test(twoparam_with_default_wrong_dec("Celia", "Yorick"), True)
        test(twoparam_with_default_wrong_dec("Celia", "Yorick"), False)

        log.info("Trying with keyword arguments and wrong key generator")
        try:
            log.info(
                twoparam_with_default_wrong_dec(a="Celia[a]", b="Yorick[b]")
            )
            raise AssertionError(
                "Inappropriate success with keyword arguments!"
            )
            _ = """
            2022-04-27: This test is failing. The call above, with named
            parameters a="Celia[a]", b="Yorick[b]", is reaching
            fkg_allowing_type_hints.generate_key() with
            args=('Celia[a]', 'Yorick[b]'), kw={}); argnames = ['a', 'b'].
            That's with Python 3.8.

            A test function works fnie in Python 3.8:

                def f(*args, **kwargs):
                    print(f"args={args!r}, kwargs={kwargs!r}")

                f(a="a", b="b")  # args=(), kwargs={'a': 'a', 'b': 'b'}
                f("a", "b")  #  args=('a', 'b'), kwargs={}
                f("a", b="b")  #  args=('a',), kwargs={'b': 'b'}

            """
        except ValueError:
            log.info("Correct rejection of keyword arguments")

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
