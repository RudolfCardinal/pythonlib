#!/usr/bin/env python
# cardinal_pythonlib/rounding.py

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
    y = (x * factor + Decimal("0.5")).quantize(
        Decimal("1"), rounding=decimal.ROUND_FLOOR
    ) / factor
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


def range_roundable_up_to(
    y: Union[int, float, Decimal], dp: int = 0, with_description: bool = False
) -> Union[Tuple[Decimal, Decimal], Tuple[Decimal, Decimal, str]]:
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
    if with_description:
        description = f"[{a}, {b})"
        return a, b, description
    else:
        return a, b


def range_truncatable_to(
    y: Union[int, float, Decimal], dp: int = 0, with_description: bool = False
) -> Union[Tuple[Decimal, Decimal], Tuple[Decimal, Decimal, str]]:
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
