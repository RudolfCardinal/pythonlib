#!/usr/bin/env python
# cardinal_pythonlib/maths_numpy.py

"""
===============================================================================

    Original code copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).

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

**Miscellaneous mathematical functions that use Numpy** (which can be slow to
load).

"""

# =============================================================================
# Imports
# =============================================================================

from collections import Counter
import random
import sys
from typing import List, Optional, Union

import numpy as np  # pip install numpy

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Constants
# =============================================================================

# sys.float_info.max_10_exp:
#       largest integer x such that 10 ** x is representable as a float
# sys.float_info.max_exp:
#       largest integer x such that float(sys.float_info.radix) ** x is
#       representable as a float... and that's 2.0 ** x
# But what we want is the largest integer x such that e ** x = math.exp(x)
# is representable as a float, and that is:

MAX_E_EXPONENT = int(np.log(sys.float_info.max))  # typically, 709


# =============================================================================
# Softmax
# =============================================================================

def softmax(x: np.ndarray,
            b: float = 1.0) -> np.ndarray:
    r"""
    Standard softmax function:

    .. math::

        P_i = \frac {e ^ {\beta \cdot x_i}} { \sum_{i}{\beta \cdot x_i} }

    Args:
        x: vector (``numpy.array``) of values
        b: exploration parameter :math:`\beta`, or inverse temperature
            [Daw2009], or :math:`1/t`; see below

    Returns:
        vector of probabilities corresponding to the input values

    where:

    - :math:`t` is temperature (towards infinity: all actions equally likely;
      towards zero: probability of action with highest value tends to 1)
    - Temperature is not used directly as optimizers may take it to zero,
      giving an infinity; use inverse temperature instead.
    - [Daw2009] Daw ND, "Trial-by-trial data analysis using computational
      methods", 2009/2011; in "Decision Making, Affect, and Learning: Attention
      and Performance XXIII"; Delgado MR, Phelps EA, Robbins TW (eds),
      Oxford University Press.

    """
    n = len(x)
    if b == 0.0:
        # e^0 / sum(a bunch of e^0) = 1 / n
        return np.full(n, 1 / n)

    constant = np.mean(x)
    products = x * b - constant
    # ... softmax is invariant to addition of a constant: Daw article and
    # http://www.faqs.org/faqs/ai-faq/neural-nets/part2/section-12.html#b
    # noinspection PyUnresolvedReferences

    if products.max() > MAX_E_EXPONENT:
        log.warning("OVERFLOW in softmax(): x = {}, b = {}, constant = {}, "
                    "x*b - constant = {}".format(x, b, constant, products))
        # map the maximum to 1, other things to zero
        index_of_max = np.argmax(products)
        answer = np.zeros(n)
        answer[index_of_max] = 1.0
        return answer

    # noinspection PyUnresolvedReferences
    exponented = np.exp(products)
    sum_exponented = np.sum(exponented)
    if sum_exponented == 0.0:
        # ... avoid division by zero
        return np.full(n, 1 / n)

    return exponented / np.sum(exponented)


def pick_from_probabilities(probabilities: Union[List[float],
                                                 np.ndarray]) -> int:
    """
    Given a list of probabilities like ``[0.1, 0.3, 0.6]``, returns the index
    of the probabilistically chosen item. In this example, we would return
    ``0`` with probability 0.1; ``1`` with probability 0.3; and ``2`` with
    probability 0.6.

    Args:
        probabilities: list of probabilities, which should sum to 1

    Returns:
        the index of the chosen option

    Raises:
        :exc:`ValueError` if a random number in the range [0, 1) is greater
        than or equal to the cumulative sum of the supplied probabilities (i.e.
        if you've specified probabilities adding up to less than 1)

    Does not object if you supply e.g. ``[1, 1, 1]``; it'll always pick the
    first in this example.

    """
    r = random.random()  # range [0.0, 1.0), i.e. 0 <= r < 1
    cs = np.cumsum(probabilities)  # e.g. [0.1, 0.4, 1] in this example
    for idx in range(len(cs)):
        if r < cs[idx]:
            return idx
    raise ValueError(
        "Probabilities sum to <1: probabilities = {!r}, "
        "cumulative sum = {!r}".format(probabilities, cs)
    )


# =============================================================================
# Logistic
# =============================================================================

def logistic(x: Union[float, np.ndarray],
             k: float,
             theta: float) -> Optional[float]:
    r"""
    Standard logistic function.

    .. math::

        y = \frac {1} {1 + e^{-k (x - \theta)}}

    Args:
        x: :math:`x`
        k: :math:`k`
        theta: :math:`\theta`

    Returns:
        :math:`y`

    """
    # https://www.sharelatex.com/learn/List_of_Greek_letters_and_math_symbols
    if x is None or k is None or theta is None:
        return None
    # noinspection PyUnresolvedReferences
    return 1 / (1 + np.exp(-k * (x - theta)))


def inv_logistic(y: Union[float, np.ndarray],
                 k: float,
                 theta: float) -> Optional[float]:
    r"""
    Inverse standard logistic function:

    .. math::

        x = ( log( \frac {1} {y} - 1) / -k ) + \theta

    Args:
        y: :math:`y`
        k: :math:`k`
        theta: :math:`\theta`

    Returns:
        :math:`x`

    """
    if y is None or k is None or theta is None:
        return None
    # noinspection PyUnresolvedReferences
    return (np.log((1 / y) - 1) / -k) + theta


# =============================================================================
# Testing
# =============================================================================

def _test_softmax() -> None:
    """
    Tests the :func`softmax` function.
    """
    arrays = [
        [1, 1],
        [1, 1, 2],
        [1, 1, 1, 1, 1.01],
        [1, 2, 3, 4, 5],
        [1, 2, 3, 4, 1000],
        [1, 2, 3, 4, 5.0 ** 400],
    ]
    betas = [
        0, 0.5, 1, 2, 10, 100,
    ]
    for x in arrays:
        for b in betas:
            y = softmax(np.array(x), b=b)
            print("softmax({x!r}, b={b}) -> {y}".format(x=x, b=b, y=y))


def _test_pick_from_probabilities() -> None:
    """
    Tests the :func:`pick_from_probabilities` function.
    """
    probabilities = [
        [0.0, 1.0],
        [0.1, 0.3, 0.6],
        [0.25, 0.25, 5],
        # [0.25],  # crashes (appropriately)
        [1, 1, 1],  # silly, but doesn't crash
    ]
    n_values = [10, 1000, 100000]
    for p in probabilities:
        for n in n_values:
            c = Counter()
            c.update(pick_from_probabilities(p) for _ in range(n))
            sc = sorted(c.items(), key=lambda kv: kv[0])
            print("_test_pick_from_probabilities: p = {p}, n = {n} "
                  "-> {sc}".format(p=p, n=n, sc=sc))


if __name__ == '__main__':
    _test_softmax()
    _test_pick_from_probabilities()
