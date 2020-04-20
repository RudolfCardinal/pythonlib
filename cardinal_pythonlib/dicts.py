#!/usr/bin/env python
# cardinal_pythonlib/dicts.py

"""
===============================================================================

    Original code copyright (C) 2009-2020 Rudolf Cardinal (rudolf@pobox.com).

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
                    f"rename_keys_in_dict: renaming {old_key!r} -> "
                    f"{new_key!r} but new key already exists")
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


# noinspection PyPep8
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


# =============================================================================
# HashableDict
# =============================================================================

class HashableDict(dict):
    """
    A dictionary that can be hashed.

    See https://stackoverflow.com/questions/1151658/python-hashable-dicts.
    """
    def __hash__(self) -> int:
        return hash(tuple(sorted(self.items())))


# =============================================================================
# CaseInsensitiveDict
# =============================================================================

class CaseInsensitiveDict(dict):
    """
    A case-insensitive dictionary, as per
    https://stackoverflow.com/questions/2082152/case-insensitive-dictionary/32888599#32888599,
    with updates for Python 3 and type hinting.
    
    See also
    
    - https://docs.python.org/3/tutorial/datastructures.html#dictionaries
    - https://docs.python.org/3/library/stdtypes.html#mapping-types-dict
    
    Test code:
    
    .. code-block:: python
    
        from cardinal_pythonlib.dicts import CaseInsensitiveDict
        
        d1 = CaseInsensitiveDict()  # d1 is now: {}
        d2 = CaseInsensitiveDict({'A': 1, 'b': 2})  # d2 is now: {'a': 1, 'b': 2}
        d3 = CaseInsensitiveDict(C=3, d=4)  # d3 is now: {'c': 3, 'd': 4}
        
        d1.update({'E': 5, 'f': 6})  # d1 is now: {'e': 5, 'f': 6}
        d1.update(G=7, h=8)  # d1 is now: {'e': 5, 'f': 6, 'g': 7, 'h': 8}
        'H' in d1  # True
        d1['I'] = 9  # None, and key 'i' added
        del d1['I']  # None, and key 'i' deleted
        d1.pop('H')  # 8
        d1.get('E')  # 5
        d1.get('Z')  # None
        d1.setdefault('J', 10)  # 10, and key 'j' added
        d1.update([('K', 11), ('L', 12)])
        d1  # {'e': 5, 'f': 6, 'g': 7, 'j': 10, 'k': 11, 'l': 12}

    """  # noqa

    @classmethod
    def _k(cls, key: Any) -> Any:
        """
        Convert key to lower case, if it's a string.
        """
        return key.lower() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs) -> None:
        """
        Dictionary initialization.

        - Optional positional argument is ``mapping`` or ``iterable``. If an
          iterable, its elements are iterables of length 2.
          (Note that passing ``None`` is different from not passing anything,
          hence the signature. The type of the first argument, if present, is
          ``Union[Mapping, Iterable[Tuple[Any, Any]]]``.)
        - Keyword arguments are key/value pairs.
        """
        super().__init__(*args, **kwargs)
        self._convert_keys()

    def __getitem__(self, key: Any) -> Any:
        """
        Given a key, return the associated value. Implements ``d[key]`` as an
        rvalue.
        """
        return super().__getitem__(self.__class__._k(key))

    def __setitem__(self, key: Any, value: Any) -> None:
        """
        Sets the value for a key. Implements ``d[key] = value``.
        """
        super().__setitem__(self.__class__._k(key), value)

    def __delitem__(self, key: Any) -> None:
        """
        Deletes the item with the specified key. Implements ``del d[key]``.
        Raises :exc:`KeyError` if absent.
        """
        super().__delitem__(self.__class__._k(key))

    def __contains__(self, key: Any) -> bool:
        """
        Is the key in the dictionary? Implements ``key in d``.
        """
        return super().__contains__(self.__class__._k(key))

    # has_key() was removed in Python 3.0
    # https://docs.python.org/3.1/whatsnew/3.0.html#builtins

    def pop(self, key: Any, *args, **kwargs) -> Any:
        """
        Retrieves/returns the item and removes it. Takes a single optional
        argument, being the default to return if the key is not present
        (otherwise raises :exc:`KeyError`). Note that supplying a default of
        ``None`` is different to supplying no default.
        """
        return super().pop(self.__class__._k(key), *args, **kwargs)

    def get(self, key: Any, default: Any = None) -> Any:
        """
        If the key is in the dictionary, return the corresponding value;
        otherwise, return ``default``, which defaults to ``None``.
        """
        return super().get(self.__class__._k(key), default)

    def setdefault(self, key: Any, default: Any = None) -> Any:
        """
        As per the Python docs:

        If ``key`` is in the dictionary, return its value. If not, insert
        ``key`` with a value of ``default`` and return ``default``. ``default``
        defaults to ``None``.
        """
        return super().setdefault(self.__class__._k(key), default)

    def update(self, *args, **kwargs) -> None:
        """
        As per the Python docs:

        Update the dictionary with the key/value pairs from ``other``,
        overwriting existing keys. Return ``None``.

        :func:`update``accepts either another dictionary object or an iterable
        of key/value pairs (as tuples or other iterables of length two). If
        keyword arguments are specified, the dictionary is then updated with
        those key/value pairs: ``d.update(red=1, blue=2)``.

        ... so the type of the first argument, if present, is ``Union[Mapping,
        .Iterable[Tuple[Any, Any]]]``.
        """
        # noinspection PyTypeChecker
        super().update(self.__class__(*args, **kwargs))

    def _convert_keys(self) -> None:
        """
        Ensure all our keys are in lower case.
        """
        for k in list(self.keys()):
            v = super().pop(k)
            self.__setitem__(k, v)
