#!/usr/bin/env python
# cardinal_pythonlib/maths_py.py

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

Miscellaneous mathematical functions in pure Python.

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
    """Return mean of a list of numbers, or None."""
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

def safe_logit(x: Union[float, int]) -> Optional[float]:
    if x > 1 or x < 0:
        return None  # can't take log of negative number
    if x == 1:
        return float("inf")
    if x == 0:
        return float("-inf")
    return math.log(x / (1 - x))
