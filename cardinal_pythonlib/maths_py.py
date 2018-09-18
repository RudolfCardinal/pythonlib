#!/usr/bin/env python
# cardinal_pythonlib/maths_py.py

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

**Miscellaneous mathematical functions in pure Python.**

"""

import logging
import math
from typing import Optional, Sequence, Union

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Mean
# =============================================================================

def mean(values: Sequence[Union[int, float, None]]) -> Optional[float]:
    """
    Returns the mean of a list of numbers.

    Args:
        values: values to mean, ignoring any values that are ``None``

    Returns:
        the mean, or ``None`` if :math:`n = 0`

    """
    total = 0.0  # starting with "0.0" causes automatic conversion to float
    n = 0
    for x in values:
        if x is not None:
            total += x
            n += 1
    return total / n if n > 0 else None


# =============================================================================
# logit
# =============================================================================

def safe_logit(p: Union[float, int]) -> Optional[float]:
    r"""
    Returns the logit (log odds) of its input probability

    .. math::

        \alpha = logit(p) = log(x / (1 - x))

    Args:
        p: :math:`p`

    Returns:
        :math:`\alpha`, or ``None`` if ``x`` is not in the range [0, 1].

    """
    if p > 1 or p < 0:
        return None  # can't take log of negative number
    if p == 1:
        return float("inf")
    if p == 0:
        return float("-inf")
    return math.log(p / (1 - p))


# =============================================================================
# Rounding
# =============================================================================

def normal_round_float(x: float, dp: int = 0) -> float:
    """
    Hmpf. Shouldn't need to have to implement this, but...

    Conventional rounding to integer via the "round half away from zero"
    method, e.g.

    .. code-block:: none

        1.1 -> 1
        1.5 -> 2
        1.6 -> 2
        2.0 -> 2

        -1.6 -> -2
        etc.

    ... or the equivalent for a certain number of decimal places.

    Note that round() implements "banker's rounding", which is never what
    we want:
    - https://stackoverflow.com/questions/33019698/how-to-properly-round-up-half-float-numbers-in-python  # noqa
    """
    if not math.isfinite(x):
        return x
    factor = pow(10, dp)
    x = x * factor
    if x >= 0:
        x = math.floor(x + 0.5)
    else:
        x = math.ceil(x - 0.5)
    x = x / factor
    return x


def normal_round_int(x: float) -> int:
    """
    Version of :func:`normal_round_float` but guaranteed to return an `int`.
    """
    if not math.isfinite(x):
        raise ValueError("Input to normal_round_int() is not finite")
    if x >= 0:
        # noinspection PyTypeChecker
        return math.floor(x + 0.5)
    else:
        # noinspection PyTypeChecker
        return math.ceil(x - 0.5)
