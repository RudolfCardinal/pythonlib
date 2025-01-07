#!/usr/bin/env python
# cardinal_pythonlib/tests/rounding_tests.py

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
# Imports
# =============================================================================

from decimal import Decimal
import unittest

from cardinal_pythonlib.rounding import (
    range_roundable_up_to,
    range_truncatable_to,
    round_half_up,
    truncate,
)


# =============================================================================
# Self-testing
# =============================================================================


def validate_range_roundable_up_to(
    x: float, dp: int, epsilon: Decimal = Decimal("1e-9")
) -> None:
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
    assert (
        b - epsilon < b
    ), f"Use a bigger value of epsilon; currently {epsilon}"
    assert round_half_up(b - epsilon, dp) == y, (
        f"round_half_up({b - epsilon}, {dp}) is "
        f"{round_half_up(b - epsilon, dp)} but should be {y}"
    )
    assert round_half_up(b, dp) > y, (
        f"round_half_up({b}, {dp}) is {round_half_up(b, dp)} "
        f"but should be >{y}"
    )


def validate_range_truncatable_to(
    x: float, dp: int, epsilon: Decimal = Decimal("1e-9")
) -> None:
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
            f"truncate({a}, {dp}) is {truncate(a, dp)} " f"but should be {y}"
        )
        assert (
            b - epsilon < b
        ), f"Use a bigger value of epsilon; currently {epsilon}"
        assert truncate(b - epsilon, dp) == y, (
            f"truncate({b - epsilon}, {dp}) is "
            f"{truncate(b - epsilon, dp)} but should be {y}"
        )
        assert truncate(b, dp) > y, (
            f"truncate({b}, {dp}) is {truncate(b, dp)} " f"but should be >{y}"
        )
    else:
        # Negative values
        assert a < x <= b
        assert (
            a + epsilon > a
        ), f"Use a bigger value of epsilon; currently {epsilon}"
        assert truncate(a, dp) < y, (
            f"truncate({a}, {dp}) is {truncate(a, dp)} " f"but should be <{y}"
        )
        assert truncate(a + epsilon, dp) == y, (
            f"truncate({a + epsilon}, {dp}) is "
            f"{truncate(a + epsilon, dp)} but should be {y}"
        )
        assert truncate(b, dp) == y, (
            f"truncate({b}, {dp}) is {truncate(b, dp)} " f"but should be {y}"
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

        assert range_roundable_up_to(Decimal("200"), -2) == (
            Decimal("150.0"),
            Decimal("250.0"),
        )
        assert range_roundable_up_to(Decimal("200"), -1) == (
            Decimal("195.0"),
            Decimal("205.0"),
        )
        assert range_roundable_up_to(Decimal("200"), 0) == (
            Decimal("199.5"),
            Decimal("200.5"),
        )
        assert range_roundable_up_to(Decimal("200"), 1) == (
            Decimal("199.95"),
            Decimal("200.05"),
        )
        assert range_roundable_up_to(Decimal("200"), 2) == (
            Decimal("199.995"),
            Decimal("200.005"),
        )

        assert range_roundable_up_to(Decimal("-1"), 0) == (
            Decimal("-1.5"),
            Decimal("-0.5"),
        )

        # range_roundable_up_to(0.5, 0)  # bad input (not correctly rounded); would assert  # noqa: E501

        for x in [Decimal("100.332"), Decimal("-150.12")]:
            for dp in [-2, -1, 0, 1, 2]:
                validate_range_roundable_up_to(x, dp, self.EPSILON)

    def test_range_truncatable_to(self) -> None:

        assert range_truncatable_to(Decimal("200"), -2) == (
            Decimal("200"),
            Decimal("300"),
        )
        assert range_truncatable_to(Decimal("200"), -1) == (
            Decimal("200"),
            Decimal("210"),
        )
        assert range_truncatable_to(Decimal("200"), 0) == (
            Decimal("200"),
            Decimal("201"),
        )
        assert range_truncatable_to(Decimal("200"), 1) == (
            Decimal("200"),
            Decimal("200.1"),
        )
        assert range_truncatable_to(Decimal("200"), 2) == (
            Decimal("200"),
            Decimal("200.01"),
        )

        assert range_truncatable_to(Decimal("-1"), 0) == (
            Decimal("-2"),
            Decimal("-1"),
        )
        assert range_truncatable_to(Decimal("-1"), 1) == (
            Decimal("-1.1"),
            Decimal("-1"),
        )
        assert range_truncatable_to(Decimal("-1"), 2) == (
            Decimal("-1.01"),
            Decimal("-1"),
        )

        # range_truncatable_to(0.5, 0)  # bad input (not correctly rounded); would assert  # noqa: E501

        for x in [Decimal("100.332"), Decimal("-150.12")]:
            for dp in [-2, -1, 0, 1, 2]:
                validate_range_truncatable_to(x, dp, self.EPSILON)
