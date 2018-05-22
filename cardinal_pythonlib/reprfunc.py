#!/usr/bin/env python
# cardinal_pythonlib/reprfunc.py

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
    Convenience function for repr().
    Works its way through the object's __dict__ and reports accordingly.
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
    Convenience function for repr().
    Works its way through a list of attribute names, and creates a repr()
    assuming that parameters to the constructor have the same names.
    """
    elements = ["{}={}".format(name, repr(getattr(obj, name)))
                for name in attrnames]
    return repr_result(obj, elements, with_addr=with_addr)


def mapped_repr(obj: Any, attributes: List[Tuple[str, str]],
                with_addr: bool = False) -> str:
    """
    Convenience function for repr().
    Takes a list of tuples: (attr_name, init_param_name).
    """
    elements = ["{}={}".format(init_param_name, repr(getattr(obj, attr_name)))
                for attr_name, init_param_name in attributes]
    return repr_result(obj, elements, with_addr=with_addr)


def mapped_repr_stripping_underscores(obj: Any, attrnames: List[str],
                                      with_addr: bool = False) -> str:
    """
    Convenience function for repr().
    Here, you pass a list of internal attributes, and it assumes that the
    __init__() parameter names have the leading underscore dropped.
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
    Shortcut to make repr() functions ordered.
    Define your repr like this:

        def __repr__(self):
            return ordered_repr(self, ["field1", "field2", "field3"])
    """
    return "<{classname}({kvp})>".format(
        classname=type(obj).__name__,
        kvp=", ".join("{}={}".format(a, repr(getattr(obj, a)))
                      for a in attrlist)
    )


def auto_str(obj: Any) -> str:
    return pprint.pformat(obj.__dict__)
