#!/usr/bin/env python
# cardinal_pythonlib/lists.py

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
"""

from collections import Counter
from typing import Any, Iterable, List


# =============================================================================
# Lists and similar
# =============================================================================

def contains_duplicates(values: Iterable[Any]) -> bool:
    for v in Counter(values).values():
        if v > 1:
            return True
    return False


def sort_list_by_index_list(x: List[Any], indexes: List[int]) -> None:
    """Re-orders x by the list of indexes of x, in place."""
    x[:] = [x[i] for i in indexes]


def flatten_list(x: List[Any]) -> List[Any]:
    return [item for sublist in x for item in sublist]
    # http://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python  # noqa


def unique_list(seq: Iterable[Any]) -> List[Any]:
    # http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-whilst-preserving-order  # noqa
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def chunks(l: List[Any], n: int) -> Iterable[List[Any]]:
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]


def count_bool(blist: Iterable[Any]) -> int:
    return sum([1 if x else 0 for x in blist])
