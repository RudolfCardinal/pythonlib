#!/usr/bin/env python
# cardinal_pythonlib/sort.py

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

**Support functions for sorting.**

"""

from functools import partial, total_ordering
import re
from typing import Any, List, Union


# =============================================================================
# Natural sorting, e.g. for COM ports
# =============================================================================
# http://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside  # noqa

def atoi(text: str) -> Union[int, str]:
    """
    Converts strings to integers if they're composed of digits; otherwise
    returns the strings unchanged. One way of sorting strings with numbers;
    it will mean that ``"11"`` is more than ``"2"``.
    """
    return int(text) if text.isdigit() else text


def natural_keys(text: str) -> List[Union[int, str]]:
    """
    Sort key function.
    Returns text split into string/number parts, for natural sorting; as per
    http://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside
    
    Example (as per the source above):
        
    .. code-block:: python
    
        >>> from cardinal_pythonlib.sort import natural_keys
        >>> alist=[
        ...     "something1",
        ...     "something12",
        ...     "something17",
        ...     "something2",
        ...     "something25",
        ...     "something29"
        ... ]
        >>> alist.sort(key=natural_keys)
        >>> alist
        ['something1', 'something2', 'something12', 'something17', 'something25', 'something29']
        
    """  # noqa
    return [atoi(c) for c in re.split('(\d+)', text)]


# =============================================================================
# Sorting where None counts as the minimum
# =============================================================================

@total_ordering
class MinType(object):
    """
    An object that compares less than anything else.
    """
    def __le__(self, other: Any) -> bool:
        return True

    def __eq__(self, other: Any) -> bool:
        return self is other


MINTYPE_SINGLETON = MinType()


# noinspection PyPep8Naming
class attrgetter_nonesort:
    """
    Modification of ``operator.attrgetter``.
    Returns an object's attributes, or the ``mintype_singleton`` if the
    attribute is ``None``.
    """
    __slots__ = ('_attrs', '_call')

    def __init__(self, attr, *attrs):
        if not attrs:
            if not isinstance(attr, str):
                raise TypeError('attribute name must be a string')
            self._attrs = (attr,)
            names = attr.split('.')

            def func(obj):
                for name in names:
                    obj = getattr(obj, name)
                if obj is None:  # MODIFIED HERE
                    return MINTYPE_SINGLETON
                return obj

            self._call = func
        else:
            self._attrs = (attr,) + attrs
            # MODIFIED HERE:
            getters = tuple(map(attrgetter_nonesort, self._attrs))

            def func(obj):
                return tuple(getter(obj) for getter in getters)

            self._call = func

    def __call__(self, obj):
        return self._call(obj)

    def __repr__(self):
        return '%s.%s(%s)' % (self.__class__.__module__,
                              self.__class__.__qualname__,
                              ', '.join(map(repr, self._attrs)))

    def __reduce__(self):
        return self.__class__, self._attrs


# noinspection PyPep8Naming
class methodcaller_nonesort:
    """
    As per :class:`attrgetter_nonesort` (q.v.), but for ``methodcaller``.
    """
    __slots__ = ('_name', '_args', '_kwargs')

    def __init__(*args, **kwargs):
        if len(args) < 2:
            msg = "methodcaller needs at least one argument, the method name"
            raise TypeError(msg)
        self = args[0]
        self._name = args[1]
        if not isinstance(self._name, str):
            raise TypeError('method name must be a string')
        self._args = args[2:]
        self._kwargs = kwargs

    def __call__(self, obj):
        # MODIFICATION HERE
        result = getattr(obj, self._name)(*self._args, **self._kwargs)
        if result is None:
            return MINTYPE_SINGLETON
        return result

    def __repr__(self):
        args = [repr(self._name)]
        args.extend(map(repr, self._args))
        args.extend('%s=%r' % (k, v) for k, v in self._kwargs.items())
        return '%s.%s(%s)' % (self.__class__.__module__,
                              self.__class__.__name__,
                              ', '.join(args))

    def __reduce__(self):
        if not self._kwargs:
            return self.__class__, (self._name,) + self._args
        else:
            return (
                partial(self.__class__, self._name, **self._kwargs),
                self._args
            )
