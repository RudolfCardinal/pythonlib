#!/usr/bin/env python
# cardinal_pythonlib/reprfunc.py

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

**Functions to assist making repr() methods for Python objects.**

"""

import pprint
from typing import Any, Iterable, List, Tuple


# =============================================================================
# __repr__ aids
# =============================================================================
# The repr() function often attempts to return something suitable for eval();
# failing that, it usually shows an address.
# https://docs.python.org/3/library/functions.html#repr

def repr_result(obj: Any, elements: List[str],
                with_addr: bool = False) -> str:
    """
    Internal function to make a :func:`repr`-style representation of an object.

    Args:
        obj: object to display
        elements: list of object ``attribute=value`` strings
        with_addr: include the memory address of ``obj``

    Returns:
        string: :func:`repr`-style representation

    """
    if with_addr:
        return "<{qualname}({elements}) at {addr}>".format(
            qualname=obj.__class__.__qualname__,
            elements=", ".join(elements),
            addr=hex(id(obj)))
    else:
        return "{qualname}({elements})".format(
            qualname=obj.__class__.__qualname__,
            elements=", ".join(elements))


def auto_repr(obj: Any, with_addr: bool = False,
              sort_attrs: bool = True) -> str:
    """
    Convenience function for :func:`__repr__`.
    Works its way through the object's ``__dict__`` and reports accordingly.

    Args:
        obj: object to display
        with_addr: include the memory address of ``obj``
        sort_attrs: sort the attributes into alphabetical order?

    Returns:
        string: :func:`repr`-style representation
    """
    if sort_attrs:
        keys = sorted(obj.__dict__.keys())
    else:
        keys = obj.__dict__.keys()
    elements = ["{}={}".format(k, repr(getattr(obj, k))) for k in keys]
    return repr_result(obj, elements, with_addr=with_addr)


def simple_repr(obj: Any, attrnames: List[str],
                with_addr: bool = False) -> str:
    """
    Convenience function for :func:`__repr__`.
    Works its way through a list of attribute names, and creates a ``repr()``
    representation assuming that parameters to the constructor have the same
    names.

    Args:
        obj: object to display
        attrnames: names of attributes to include
        with_addr: include the memory address of ``obj``

    Returns:
        string: :func:`repr`-style representation

    """
    elements = ["{}={}".format(name, repr(getattr(obj, name)))
                for name in attrnames]
    return repr_result(obj, elements, with_addr=with_addr)


def mapped_repr(obj: Any, attributes: List[Tuple[str, str]],
                with_addr: bool = False) -> str:
    """
    Convenience function for :func:`__repr__`.
    Takes attribute names and corresponding initialization parameter names
    (parameters to :func:`__init__`).

    Args:
        obj: object to display
        attributes: list of tuples, each ``(attr_name, init_param_name)``.
        with_addr: include the memory address of ``obj``

    Returns:
        string: :func:`repr`-style representation

    """
    elements = ["{}={}".format(init_param_name, repr(getattr(obj, attr_name)))
                for attr_name, init_param_name in attributes]
    return repr_result(obj, elements, with_addr=with_addr)


def mapped_repr_stripping_underscores(obj: Any, attrnames: List[str],
                                      with_addr: bool = False) -> str:
    """
    Convenience function for :func:`__repr__`.
    Here, you pass a list of internal attributes, and it assumes that the
    :func:`__init__` parameter names have the leading underscore dropped.

    Args:
        obj: object to display
        attrnames: list of attribute names
        with_addr: include the memory address of ``obj``

    Returns:
        string: :func:`repr`-style representation

    """
    attributes = []
    for attr_name in attrnames:
        if attr_name.startswith('_'):
            init_param_name = attr_name[1:]
        else:
            init_param_name = attr_name
        attributes.append((attr_name, init_param_name))
    return mapped_repr(obj, attributes, with_addr=with_addr)


def ordered_repr(obj: object, attrlist: Iterable[str]) -> str:
    """
    Shortcut to make :func:`repr` functions ordered.
    Define your :func:`__repr__` like this:

    .. code-block:: python

        def __repr__(self):
            return ordered_repr(self, ["field1", "field2", "field3"])

    Args:
        obj: object to display
        attrlist: iterable of attribute names

    Returns:
        string: :func:`repr`-style representation
    """
    return "<{classname}({kvp})>".format(
        classname=type(obj).__name__,
        kvp=", ".join("{}={}".format(a, repr(getattr(obj, a)))
                      for a in attrlist)
    )


def auto_str(obj: Any) -> str:
    """
    Make a pretty :func:`str()` representation using :func:`pprint.pformat`.

    Args:
        obj: object to display

    Returns:
        string: :func:`str`-style representation

    """
    return pprint.pformat(obj.__dict__)
