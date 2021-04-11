#!/usr/bin/env python
# cardinal_pythonlib/iterhelp.py

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

**Iteration assistance functions.**

"""

from itertools import product
from typing import Dict, Iterable


def product_dict(**kwargs: Iterable) -> Iterable[Dict]:
    """
    See
    https://stackoverflow.com/questions/5228158/cartesian-product-of-a-dictionary-of-lists.

    Takes keyword arguments, and yields dictionaries containing every
    combination of possibilities for each keyword.

    Examples:

    .. code-block:: python

        >>> list(product_dict(a=[1, 2], b=[3, 4]))
        [{'a': 1, 'b': 3}, {'a': 1, 'b': 4}, {'a': 2, 'b': 3}, {'a': 2, 'b': 4}]

        >>> list(product_dict(a="x", b=range(3)))
        [{'a': 'x', 'b': 0}, {'a': 'x', 'b': 1}, {'a': 'x', 'b': 2}]

        >>> product_dict(a="x", b=range(3))
        <generator object product_dict at 0x7fb328070678>
    """  # noqa
    keys = kwargs.keys()
    vals = kwargs.values()
    for instance in product(*vals):
        yield dict(zip(keys, instance))
