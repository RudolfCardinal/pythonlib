#!/usr/bin/env python
# cardinal_pythonlib/dicts.py

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

**Dictionary manipulations.**

"""

from typing import Any, Callable, Dict, Hashable, List, Optional


# =============================================================================
# Dictionaries
# =============================================================================

def get_case_insensitive_dict_key(d: Dict, k: str) -> Optional[str]:
    """
    Within the dictionary ``d``, find a key that matches (in case-insensitive
    fashion) the key ``k``, and return it (or ``None`` if there isn't one).
    """
    for key in d.keys():
        if k.lower() == key.lower():
            return key
    return None


def merge_dicts(*dict_args: Dict) -> Dict:
    """
    Given any number of dicts, shallow-copy them and merge into a new dict.
    Precedence goes to key/value pairs in dicts that are later in the list.

    See http://stackoverflow.com/questions/38987.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def merge_two_dicts(x: Dict, y: Dict) -> Dict:
    """
    Given two dicts, merge them into a new dict as a shallow copy, e.g.

    .. code-block:: python

        z = merge_two_dicts(x, y)

    If you can guarantee Python 3.5, then a simpler syntax is:

    .. code-block:: python

        z = {**x, **y}

    See http://stackoverflow.com/questions/38987.
    """
    z = x.copy()
    z.update(y)
    return z


def rename_key(d: Dict[str, Any], old: str, new: str) -> None:
    """
    Rename a key in dictionary ``d`` from ``old`` to ``new``, in place.
    """
    d[new] = d.pop(old)


def rename_keys(d: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Returns a copy of the dictionary ``d`` with its keys renamed according to
    ``mapping``.

    Args:
        d: the starting dictionary
        mapping: a dictionary of the format ``{old_key_name: new_key_name}``

    Returns:
        a new dictionary

    Keys that are not in ``mapping`` are left unchanged.
    The input parameters are not modified.
    """
    result = {}  # type: Dict[str, Any]
    for k, v in d.items():
        if k in mapping:
            k = mapping[k]
        result[k] = v
    return result


def rename_keys_in_dict(d: Dict[str, Any], renames: Dict[str, str]) -> None:
    """
    Renames, IN PLACE, the keys in ``d`` according to the mapping in
    ``renames``.
    
    Args:
        d: a dictionary to modify 
        renames: a dictionary of the format ``{old_key_name: new_key_name}``
        
    See
    https://stackoverflow.com/questions/4406501/change-the-name-of-a-key-in-dictionary.
    """  # noqa
    for old_key, new_key in renames.items():
        if new_key == old_key:
            continue
        if old_key in d:
            if new_key in d:
                raise ValueError(
                    "rename_keys_in_dict: renaming {} -> {} but new key "
                    "already exists".format(repr(old_key), repr(new_key)))
            d[new_key] = d.pop(old_key)


def prefix_dict_keys(d: Dict[str, Any], prefix: str) -> Dict[str, Any]:
    """
    Returns a dictionary that's a copy of as ``d`` but with ``prefix``
    prepended to its keys.
    """
    result = {}  # type: Dict[str, Any]
    for k, v in d.items():
        result[prefix + k] = v
    return result


def reversedict(d: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Takes a ``k -> v`` mapping and returns a ``v -> k`` mapping.
    """
    return {v: k for k, v in d.items()}


def set_null_values_in_dict(d: Dict[str, Any],
                            null_literals: List[Any]) -> None:
    """
    Within ``d`` (in place), replace any values found in ``null_literals`` with
    ``None``.
    """
    if not null_literals:
        return
    # DO NOT add/delete values to/from a dictionary during iteration, but it
    # is OK to modify existing keys:
    #       https://stackoverflow.com/questions/6777485
    #       https://stackoverflow.com/questions/2315520
    #       https://docs.python.org/3/library/stdtypes.html#dict-views
    for k, v in d.items():
        if v in null_literals:
            d[k] = None


def map_keys_to_values(l: List[Any], d: Dict[Any, Any], default: Any = None,
                       raise_if_missing: bool = False,
                       omit_if_missing: bool = False) -> List[Any]:
    """
    The ``d`` dictionary contains a ``key -> value`` mapping.

    We start with a list of potential keys in ``l``, and return a list of
    corresponding values -- substituting ``default`` if any are missing,
    or raising :exc:`KeyError` if ``raise_if_missing`` is true, or omitting the
    entry if ``omit_if_missing`` is true.
    """
    result = []
    for k in l:
        if raise_if_missing and k not in d:
            raise ValueError("Missing key: " + repr(k))
        if omit_if_missing and k not in d:
            continue
        result.append(d.get(k, default))
    return result


def dict_diff(d1: Dict[Any, Any], d2: Dict[Any, Any],
              deleted_value: Any = None) -> Dict[Any, Any]:
    """
    Returns a representation of the changes that need to be made to ``d1`` to
    create ``d2``.

    Args:
        d1: a dictionary
        d2: another dictionary
        deleted_value: value to use for deleted keys; see below

    Returns:
        dict: a dictionary of the format ``{k: v}`` where the ``k``/``v`` pairs
        are key/value pairs that are absent from ``d1`` and present in ``d2``,
        or present in both but with different values (in which case the ``d2``
        value is shown). If a key ``k`` is present in ``d1`` but absent in
        ``d2``, the result dictionary has the entry ``{k: deleted_value}``.

    """
    changes = {k: v for k, v in d2.items()
               if k not in d1 or d2[k] != d1[k]}
    for k in d1.keys():
        if k not in d2:
            changes[k] = deleted_value
    return changes


def delete_keys(d: Dict[Any, Any],
                keys_to_delete: List[Any],
                keys_to_keep: List[Any]) -> None:
    """
    Deletes keys from a dictionary, in place.

    Args:
        d:
            dictonary to modify
        keys_to_delete:
            if any keys are present in this list, they are deleted...
        keys_to_keep:
            ... unless they are present in this list.
    """
    for k in keys_to_delete:
        if k in d and k not in keys_to_keep:
            del d[k]


# =============================================================================
# Lazy dictionaries
# =============================================================================

class LazyDict(dict):
    """
    A dictionary that only evaluates the argument to :func:`setdefault` or
    :func:`get` if it needs to.
    
    See
    https://stackoverflow.com/questions/17532929/how-to-implement-a-lazy-setdefault.
    
    The ``*args``/``**kwargs`` parts are useful, but we don't want to have to
    name 'thunk' explicitly.
    """  # noqa
    def get(self, key: Hashable, thunk: Any = None,
            *args: Any, **kwargs: Any) -> Any:
        if key in self:
            return self[key]
        elif callable(thunk):
            return thunk(*args, **kwargs)
        else:
            return thunk

    def setdefault(self, key: Hashable, thunk: Any = None,
                   *args: Any, **kwargs: Any) -> Any:
        if key in self:
            return self[key]
        elif callable(thunk):
            return dict.setdefault(self, key, thunk(*args, **kwargs))
        else:
            return dict.setdefault(self, key, thunk)


class LazyButHonestDict(dict):
    """
    A dictionary that provides alternatives to :func:`get` and
    :func:`setdefault`, namely :func:`lazyget` and :func:`lazysetdefault`,
    that only evaluate their arguments if they have to.

    See
    https://stackoverflow.com/questions/17532929/how-to-implement-a-lazy-setdefault.

    Compared to the StackOverflow version: no obvious need to have a default
    returning ``None``, when we're implementing this as a special function.
    In contrast, helpful to have ``*args``/``**kwargs`` options.
    """  # noqa
    def lazyget(self, key: Hashable, thunk: Callable,
                *args: Any, **kwargs: Any) -> Any:
        if key in self:
            return self[key]
        else:
            return thunk(*args, **kwargs)

    def lazysetdefault(self, key: Hashable, thunk: Callable,
                       *args: Any, **kwargs: Any) -> Any:
        if key in self:
            return self[key]
        else:
            return self.setdefault(key, thunk(*args, **kwargs))
