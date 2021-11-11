#!/usr/bin/env python
# cardinal_pythonlib/rounding.py

"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

**Rounding functions.**

Note the general need to use ``Decimal``, not ``float``; otherwise rounding
errors get silly, e.g. ``-150.1 + 0.05 == -150.04999999999998``.

"""

# =============================================================================
# Imports
# =============================================================================

import decimal
from decimal import Decimal
from typing import Tuple, Union
import unittest


# =============================================================================
# Rounding/truncation
# =============================================================================

def round_half_up(x: Union[float, Decimal], dp: int = 0) -> Decimal:
    """
    Rounds, with halves going up (positive).

    (That is not the same as ``ROUND_HALF_UP`` in the ``decimal`` module!)

    See also other methods, e.g.

    - https://en.wikipedia.org/wiki/Rounding
    - https://kodify.net/python/math/round-decimals/
    - https://stackoverflow.com/questions/33019698/how-to-properly-round-up-half-float-numbers-in-python

    """  # noqa
    x = Decimal(x)
    context = decimal.getcontext()
    factor = context.power(10, dp)
    y = (
        x * factor + Decimal("0.5")
    ).quantize(Decimal("1"), rounding=decimal.ROUND_FLOOR) / factor
    # print(f"round_half_up({x}, {dp}) = {y}")
    return y


def truncate(x: Union[float, Decimal], dp: int = 0) -> Decimal:
    """
    Truncates a value to a certain number of decimal places.
    """
    x = Decimal(x)
    context = decimal.getcontext()
    factor = context.power(10, dp)
    if x >= 0:
        rounding = decimal.ROUND_FLOOR
    else:
        # Negative x
        rounding = decimal.ROUND_CEILING
    y = (x * factor).quantize(Decimal("1"), rounding=rounding) / factor
    # print(f"truncate(x={x}, dp={dp}) = {y}")
    return y


# =============================================================================
# Reverse rounding/truncation
# =============================================================================

def remove_exponent_from_decimal(d: Decimal) -> Decimal:
    """
    Converts a decimal like ``5.0E+3`` to ``5000``.
    As per https://docs.python.org/3/library/decimal.html.
    """
    return d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize()


def num_dp_from_decimal(x: Decimal, with_negative_dp: bool = False) -> int:
    """
    Return the number of decimal places used by a ``Decimal``.

    By default, this is what you'd expect; e.g. ``123.45`` has 2 dp, and
    ``120`` has 0 dp. But if you set ``with_negative_dp`` to ``True``, then you
    if you pass in ``200`` you will get the answer ``-2``.

    Beware using ``str()``; Decimals can look like ``1E+2`` rather than
    ``100``.
    """
    components = str(remove_exponent_from_decimal(x)).split(".")
    if len(components) == 1:
        # No component after the decimal point.
        if with_negative_dp:
            before_period = components[0]
            num_zeros = len(before_period) - len(before_period.rstrip("0"))
            return -num_zeros
        else:
            return 0
    return len(components[1])


def range_roundable_up_to(y: Union[int, float, Decimal],
                          dp: int = 0,
                          with_description: bool = False) \
        -> Union[Tuple[Decimal, Decimal], Tuple[Decimal, Decimal, str]]:
    """
    Suppose some value ``x`` was rounded to ``y`` with ``dp`` decimal places,
    using the "round half up" rounding method (see implementation in
    :func:`round_half_up`).

    Given ``y`` and ``dp``, this function finds the range ``[a, b)``, such that
    ``a <= b``, within which ``x`` must have lain. The tuple returned is ``a,
    b``.

    If ``with_description`` is true, the tuple returned is ``a, b,
    range_description``.

    There are a large variety of rounding methods; see
    https://en.wikipedia.org/wiki/Rounding.
    Watch out -- Python's :func:`round` and Numpy's :func:`np.around` don't do
    that. See
    https://stackoverflow.com/questions/33019698/how-to-properly-round-up-half-float-numbers-in-python.

    Note that ``dp`` can be negative, as in other Python functions.

    """  # noqa
    y = Decimal(y)
    assert num_dp_from_decimal(y, with_negative_dp=True) <= dp, (
        f"Number {y} is not rounded to {dp} dp as claimed; it has "
        f"{num_dp_from_decimal(y, with_negative_dp=True)} dp"
    )
    half = Decimal("0.5") * decimal.getcontext().power(10, -dp)
    a = y - half
    b = y + half
    # print(f"range_roundable_up_to(y={y}, dp={dp}): half={half}, a={a}, b={b}")  # noqa
    if with_description:
        description = f"[{a}, {b})"
        return a, b, description
    else:
        return a, b


def range_truncatable_to(y: Union[int, float, Decimal],
                         dp: int = 0,
                         with_description: bool = False) \
        -> Union[Tuple[Decimal, Decimal], Tuple[Decimal, Decimal, str]]:
    """
    Some value ``x`` was truncated to ``y`` with ``dp`` decimal places, as per
    the implementation in :func:`truncate`. Return the range within which ``x``
    must have lain.

    The tuple returned is ``a, b``, such that ``a <= b``.

    If ``with_description`` is true, the tuple returned is ``a, b,
    range_description``.

    If ``y`` is positive, the range returned is ``[a, b)``.
    If ``y`` is negative, the range returned is ``(a, b]``.

    Note that ``dp`` can be negative, as in other Python functions.
    """
    y = Decimal(y)
    assert num_dp_from_decimal(y, with_negative_dp=True) <= dp, (
        f"Number {y} is not truncated to {dp} dp as claimed; it has "
        f"{num_dp_from_decimal(y, with_negative_dp=True)} dp"
    )
    one = decimal.getcontext().power(10, -dp)
    if y >= 0:
        a = y  # inclusive
        b = y + one  # exclusive
    else:
        # Negative y
        a = y - one  # exclusive
        b = y  # inclusive
    if with_description:
        description = f"[{a}, {b})" if y >= 0 else f"({a}, {b}]"
        return a, b, description
    else:
        return a, b


# =============================================================================
# Self-testing
# =============================================================================

def validate_range_roundable_up_to(x: float, dp: int,
                                   epsilon: Decimal = Decimal("1e-9")) -> None:
    """
    Checks assumptions for :func:`range_roundable_up_to`.

    Args:
        x: number to be rounded
        dp: number of decimal places
        epsilon: small value to check boundaries
    """
    y = round_half_up(x, dp)
    a, b, description = range_roundable_up_to(y, dp, with_description=True)
    print(
        f"validate_range_roundable_up_to: (1) x={x}, dp={dp}; "
        f"(2) y = round_half_up(x, dp) = {y}; "
        f"(3) range_roundable_up_to(y, dp) = {description}"
    )
    assert a <= x < b
    assert round_half_up(a, dp) == y, (
        f"round_half_up({a}, {dp}) is {round_half_up(a, dp)} "
        f"but should be {y}"
    )
    assert b - epsilon < b, (
        f"Use a bigger value of epsilon; currently {epsilon}"
    )
    assert round_half_up(b - epsilon, dp) == y, (
        f"round_half_up({b - epsilon}, {dp}) is "
        f"{round_half_up(b - epsilon, dp)} but should be {y}"
    )
    assert round_half_up(b, dp) > y, (
        f"round_half_up({b}, {dp}) is {round_half_up(b, dp)} "
        f"but should be >{y}"
    )


def validate_range_truncatable_to(x: float, dp: int,
                                  epsilon: Decimal = Decimal("1e-9")) -> None:
    """
    Checks assumptions for :func:`range_roundable_up_to`.

    Args:
        x: number to be truncated
        dp: number of decimal places
        epsilon: small value to check boundaries
    """
    y = truncate(x, dp)
    a, b, description = range_truncatable_to(y, dp, with_description=True)
    print(
        f"validate_range_truncatable_to: (1) x={x}, dp={dp}; "
        f"(2) y = truncate(x, dp) = {y}; "
        f"(3) range_truncatable_to(y, dp) = {description}"
    )
    if y >= 0:
        assert a <= x < b
        assert truncate(a, dp) == y, (
            f"truncate({a}, {dp}) is {truncate(a, dp)} "
            f"but should be {y}"
        )
        assert b - epsilon < b, (
            f"Use a bigger value of epsilon; currently {epsilon}"
        )
        assert truncate(b - epsilon, dp) == y, (
            f"truncate({b - epsilon}, {dp}) is "
            f"{truncate(b - epsilon, dp)} but should be {y}"
        )
        assert truncate(b, dp) > y, (
            f"truncate({b}, {dp}) is {truncate(b, dp)} "
            f"but should be >{y}"
        )
    else:
        # Negative values
        assert a < x <= b
        assert a + epsilon > a, (
            f"Use a bigger value of epsilon; currently {epsilon}"
        )
        assert truncate(a, dp) < y, (
            f"truncate({a}, {dp}) is {truncate(a, dp)} "
            f"but should be <{y}"
        )
        assert truncate(a + epsilon, dp) == y, (
            f"truncate({a + epsilon}, {dp}) is "
            f"{truncate(a + epsilon, dp)} but should be {y}"
        )
        assert truncate(b, dp) == y, (
            f"truncate({b}, {dp}) is {truncate(b, dp)} "
            f"but should be {y}"
        )


class TestRoundingAndReversal(unittest.TestCase):
    EPSILON = Decimal("1e-9")

    def test_round_half_up(self) -> None:
        assert round_half_up(Decimal("-123.51"), 0) == Decimal("-124.0")
        assert round_half_up(Decimal("-123.5"), 0) == Decimal("-123.0")
        assert round_half_up(Decimal("-123.49"), 0) == Decimal("-123.0")

        assert round_half_up(Decimal("-123.456"), -1) == Decimal("-120.0")
        assert round_half_up(Decimal("-123.456"), 0) == Decimal("-123.0")
        assert round_half_up(Decimal("-123.456"), 1) == Decimal("-123.5")

        assert round_half_up(Decimal("-0.51"), 0) == Decimal("-1.0")
        assert round_half_up(Decimal("-0.5"), 0) == Decimal("0.0")
        assert round_half_up(Decimal("-0.49"), 0) == Decimal("0.0")
        assert round_half_up(Decimal("0.49"), 0) == Decimal("0.0")
        assert round_half_up(Decimal("0.49"), 0) == Decimal("0.0")
        assert round_half_up(Decimal("0.5"), 0) == Decimal("1.0")

        assert round_half_up(Decimal("123.456"), -1) == Decimal("120.0")
        assert round_half_up(Decimal("123.456"), 0) == Decimal("123.0")
        assert round_half_up(Decimal("123.456"), 1) == Decimal("123.5")

    def test_truncate(self) -> None:

        assert truncate(Decimal("-123.456"), -1) == Decimal("-120.0")
        assert truncate(Decimal("-123.456"), 0) == Decimal("-123.0")
        assert truncate(Decimal("-123.456"), 1) == Decimal("-123.4")

        assert truncate(Decimal("-0.51"), 0) == Decimal("0.0")
        assert truncate(Decimal("-0.5"), 0) == Decimal("0.0")
        assert truncate(Decimal("-0.49"), 0) == Decimal("0.0")
        assert truncate(Decimal("0.49"), 0) == Decimal("0.0")
        assert truncate(Decimal("0.49"), 0) == Decimal("0.0")
        assert truncate(Decimal("0.5"), 0) == Decimal("0.0")

        assert truncate(Decimal("123.456"), -1) == Decimal("120.0")
        assert truncate(Decimal("123.456"), 0) == Decimal("123.0")
        assert truncate(Decimal("123.456"), 1) == Decimal("123.4")

    def test_range_roundable_up_to(self) -> None:

        assert range_roundable_up_to(Decimal("200"), -2) == \
               (Decimal("150.0"), Decimal("250.0"))
        assert range_roundable_up_to(Decimal("200"), -1) == \
               (Decimal("195.0"), Decimal("205.0"))
        assert range_roundable_up_to(Decimal("200"), 0) == \
               (Decimal("199.5"), Decimal("200.5"))
        assert range_roundable_up_to(Decimal("200"), 1) == \
               (Decimal("199.95"), Decimal("200.05"))
        assert range_roundable_up_to(Decimal("200"), 2) == \
               (Decimal("199.995"), Decimal("200.005"))

        assert range_roundable_up_to(Decimal("-1"), 0) == \
               (Decimal("-1.5"), Decimal("-0.5"))

        # range_roundable_up_to(0.5, 0)  # bad input (not correctly rounded); would assert  # noqa

        for x in [Decimal("100.332"), Decimal("-150.12")]:
            for dp in [-2, -1, 0, 1, 2]:
                validate_range_roundable_up_to(x, dp, self.EPSILON)

    def test_range_truncatable_to(self) -> None:

        assert range_truncatable_to(Decimal("200"), -2) == \
               (Decimal("200"), Decimal("300"))
        assert range_truncatable_to(Decimal("200"), -1) == \
               (Decimal("200"), Decimal("210"))
        assert range_truncatable_to(Decimal("200"), 0) == \
               (Decimal("200"), Decimal("201"))
        assert range_truncatable_to(Decimal("200"), 1) == \
               (Decimal("200"), Decimal("200.1"))
        assert range_truncatable_to(Decimal("200"), 2) == \
               (Decimal("200"), Decimal("200.01"))

        assert range_truncatable_to(Decimal("-1"), 0) == \
               (Decimal("-2"), Decimal("-1"))
        assert range_truncatable_to(Decimal("-1"), 1) == \
               (Decimal("-1.1"), Decimal("-1"))
        assert range_truncatable_to(Decimal("-1"), 2) == \
               (Decimal("-1.01"), Decimal("-1"))

        # range_truncatable_to(0.5, 0)  # bad input (not correctly rounded); would assert  # noqa

        for x in [Decimal("100.332"), Decimal("-150.12")]:
            for dp in [-2, -1, 0, 1, 2]:
                validate_range_truncatable_to(x, dp, self.EPSILON)


# =============================================================================
# Command-line entry point
# =============================================================================

if __name__ == "__main__":
    unittest.main()
