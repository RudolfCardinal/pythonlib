#!/usr/bin/env python
# cardinal_pythonlib/maths_numpy.py

"""
===============================================================================
    Copyright (C) 2009-2017 Rudolf Cardinal (rudolf@pobox.com).

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

Miscellaneous mathematical functions that use Numpy (which can be slow to
load).

"""

# =============================================================================
# Imports
# =============================================================================

import logging
import sys
from typing import Optional, Union

import numpy as np  # pip install numpy

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Softmax
# =============================================================================

def softmax(x: np.ndarray,
            b: float = 1.0) -> np.ndarray:
    # x: vector (numpy.array) of values
    # b: exploration parameter, or inverse temperature [Daw2009], or 1/t where:
    # t: temperature (towards infinity: all actions equally likely;
    #       towards zero: probability of action with highest value tends to 1)
    # DO NOT USE TEMPERATURE DIRECTLY: optimizers may take it to zero,
    #       giving an infinity.
    # return value: vector of probabilities
    constant = np.mean(x)
    products = x * b - constant
    # ... softmax is invariant to addition of a constant: Daw article and
    # http://www.faqs.org/faqs/ai-faq/neural-nets/part2/section-12.html#b
    # noinspection PyUnresolvedReferences
    if products.max() > sys.float_info.max_exp:
        # ... max_exp for base e; max_10_exp for base 10
        log.warning("OVERFLOW in softmax(): x = {}, b = {}, constant = {}, "
                    "x*b - constant = {}".format(x, b, constant, products))
        # map the maximum to 1, other things to zero
        n = len(x)
        index_of_max = np.argmax(products)
        answer = np.zeros(n)
        answer[index_of_max] = 1.0
    else:
        # noinspection PyUnresolvedReferences
        exponented = np.exp(products)
        answer = exponented / np.sum(exponented)
    return answer


# =============================================================================
# Logistic
# =============================================================================

def logistic(x: Union[float, np.ndarray],
             k: float,
             theta: float) -> Optional[float]:
    """Standard logistic function."""
    if x is None or k is None or theta is None:
        return None
    # noinspection PyUnresolvedReferences
    return 1 / (1 + np.exp(-k * (x - theta)))


def inv_logistic(y: Union[float, np.ndarray],
                 k: float,
                 theta: float) -> Optional[float]:
    """Inverse standard logistic function."""
    if y is None or k is None or theta is None:
        return None
    # noinspection PyUnresolvedReferences
    return (np.log((1 / y) - 1) / -k) + theta


# =============================================================================
# Testing
# =============================================================================

if __name__ == '__main__':
    sep = "=" * 79
    print(sep)
    print("Test softmax")
    print(sep)

    x1 = np.array([1, 2, 3, 4, 5.0**400])
    x2 = np.array([1, 2, 3, 4, 5])
    x3 = np.array([1, 1, 1, 1, 1.01])
    print(softmax(x1))
    print(softmax(x2))
    print(softmax(x3))
    print(softmax(x3, b=100.0))
