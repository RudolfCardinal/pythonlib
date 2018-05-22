#!/usr/bin/env python
# cardinal_pythonlib/lists.py

"""
===============================================================================
    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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
from operator import itemgetter
from typing import Any, Callable, Iterable, List, Tuple


# =============================================================================
# Lists and similar
# =============================================================================

def contains_duplicates(values: Iterable[Any]) -> bool:
    for v in Counter(values).values():
        if v > 1:
            return True
    return False


def index_list_for_sort_order(x: List[Any], key: Callable[[Any], Any] = None,
                              reverse: bool = False) -> List[int]:
    """
    Returns a list of indexes of x, IF x WERE TO BE SORTED.

z = ["a", "c", "b"]
index_list_for_sort_order(z)  # [0, 2, 1]
index_list_for_sort_order(z, reverse=True)  # [1, 2, 0]
q = [("a", 9), ("b", 8), ("c", 7)]
index_list_for_sort_order(q, key=itemgetter(1))

    """
    def key_with_user_func(idx_val: Tuple[int, Any]):
        return key(idx_val[1])
    if key:
        sort_key = key_with_user_func
        # see the simpler version below
    else:
        sort_key = itemgetter(1)
        # enumerate, below, will return tuples of (index, value), so
        # itemgetter(1) means sort by the value
    index_value_list = sorted(enumerate(x), key=sort_key, reverse=reverse)
    return [i for i, _ in index_value_list]


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
