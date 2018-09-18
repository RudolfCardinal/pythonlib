#!/usr/bin/env python
# cardinal_pythonlib/lists.py

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

**Functions for dealing with lists.**

"""

from collections import Counter
from operator import itemgetter
from typing import Any, Callable, Iterable, List, Tuple


# =============================================================================
# Lists and similar
# =============================================================================

def contains_duplicates(values: Iterable[Any]) -> bool:
    """
    Does the iterable contain any duplicate values?
    """
    for v in Counter(values).values():
        if v > 1:
            return True
    return False


def index_list_for_sort_order(x: List[Any], key: Callable[[Any], Any] = None,
                              reverse: bool = False) -> List[int]:
    """
    Returns a list of indexes of ``x``, IF ``x`` WERE TO BE SORTED.

    Args:
        x: data
        key: function to be applied to the data to generate a sort key; this
            function is passed as the ``key=`` parameter to :func:`sorted`;
            the default is ``itemgetter(1)``
        reverse: reverse the sort order?

    Returns:
        list of integer index values

    Example:

    .. code-block:: python

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
    """
    Re-orders ``x`` by the list of ``indexes`` of ``x``, in place.

    Example:

    .. code-block:: python

        from cardinal_pythonlib.lists import sort_list_by_index_list

        z = ["a", "b", "c", "d", "e"]
        sort_list_by_index_list(z, [4, 0, 1, 2, 3])
        z  # ["e", "a", "b", "c", "d"]
    """
    x[:] = [x[i] for i in indexes]


def flatten_list(x: List[Any]) -> List[Any]:
    """
    Converts a list of lists into a flat list.
    
    Args:
        x: list of lists 

    Returns:
        flat list
        
    As per
    http://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python

    """  # noqa
    return [item for sublist in x for item in sublist]


def unique_list(seq: Iterable[Any]) -> List[Any]:
    """
    Returns a list of all the unique elements in the input list.

    Args:
        seq: input list

    Returns:
        list of unique elements

    As per
    http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-whilst-preserving-order

    """  # noqa
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def chunks(l: List[Any], n: int) -> Iterable[List[Any]]:
    """
    Yield successive ``n``-sized chunks from ``l``.

    Args:
        l: input list
        n: chunk size

    Yields:
        successive chunks of size ``n``

    """
    for i in range(0, len(l), n):
        yield l[i:i + n]


def count_bool(blist: Iterable[Any]) -> int:
    """
    Counts the number of "truthy" members of the input list.

    Args:
        blist: list of booleans or other truthy/falsy things

    Returns:
        number of truthy items

    """
    return sum([1 if x else 0 for x in blist])
