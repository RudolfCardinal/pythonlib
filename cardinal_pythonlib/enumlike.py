#!/usr/bin/env python
# cardinal_pythonlib/enumlike.py

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

**Enum-based classes**

See https://docs.python.org/3/library/enum.html.

The good things about enums are:

- they are immutable
- they are "class-like", not "instance-like"
- they can be accessed via attribute (like an object) or item (like a dict):
- you can add a ``@unique`` decorator to ensure no two have the same value
- IDEs know about them

``AttrDict``'s disadvantages are:

- more typing / DRY
- IDEs don't know about them

Plain old objects:

- not immutable
- no dictionary access -- though can use ``getattr()``
- but otherwise simpler than enums

LowerCaseAutoStringObject:

- IDEs don't understand their values, so get types wrong

.. code-block:: python

    from enum import Enum

    class Colour(Enum):
        red = 1
        green = 2
        blue = 3

    Colour.red  # <Colour.red: 1>
    Colour.red.name  # 'red'
    Colour.red.value  # 1
    Colour['red']  # <Colour.red: 1>

    Colour.red = 4  # AttributeError: Cannot reassign members.

Then, for fancier things below, note that:

.. code-block:: none

    metaclass
        __prepare__(mcs, name, bases)
            ... prepares (creates) the class namespace
            ... use if you don't want the namespace to be a plain dict()
            ... https://docs.python.org/3/reference/datamodel.html
            ... returns the (empty) namespace
        __new__(mcs, name, bases, namespace)
            ... called with the populated namespace
            ... makes and returns the class object, cls

    class
        __new__(cls)
            ... controls the creation of a new instance; static classmethod
            ... makes self

        __init__(self)
            ... controls the initialization of an instance


"""

import collections
from collections import OrderedDict
from enum import EnumMeta, Enum
import itertools
from typing import Any, List, Optional, Tuple, Type

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler
from cardinal_pythonlib.reprfunc import ordered_repr

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Enum-based classes
# =============================================================================

STR_ENUM_FWD_REF = "StrEnum"
# class name forward reference for type checker:
# http://mypy.readthedocs.io/en/latest/kinds_of_types.html
# ... but also: a variable (rather than a string literal) stops PyCharm giving
# the curious error "PEP 8: no newline at end of file" and pointing to the
# type hint string literal.


class StrEnum(Enum):
    """
    StrEnum:

    - makes ``str(myenum.x)`` give ``str(myenum.x.value)``
    - adds a lookup function (from a string literal)
    - adds ordering by value

    """
    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def lookup(cls,
               value: Any,
               allow_none: bool = False) -> Optional[STR_ENUM_FWD_REF]:
        for item in cls:
            if value == item.value:
                return item
        if not value and allow_none:
            return None
        raise ValueError(
            f"Value {value!r} not found in enum class {cls.__name__}")

    def __lt__(self, other: STR_ENUM_FWD_REF) -> bool:
        return str(self) < str(other)


# -----------------------------------------------------------------------------
# EnumDict and support functions from Python 3.6
# -----------------------------------------------------------------------------

_auto_null = object()


class _Auto:
    """
    Instances are replaced with an appropriate value in Enum class suites.
    """
    value = _auto_null


def _is_descriptor(obj):
    """
    A copy of enum._is_descriptor from Python 3.6.

    Returns True if obj is a descriptor, False otherwise.
    """
    return (
            hasattr(obj, '__get__') or
            hasattr(obj, '__set__') or
            hasattr(obj, '__delete__'))


def _is_dunder(name):
    """
    A copy of enum._is_dunder from Python 3.6.

    Returns True if a __dunder__ (double underscore) name, False otherwise.
    """
    return (len(name) > 4 and
            name[:2] == name[-2:] == '__' and
            name[2] != '_' and
            name[-3] != '_')


def _is_sunder(name):
    """
    A copy of enum._is_sunder from Python 3.6.

    Returns True if a _sunder_ (single underscore) name, False otherwise.
    """
    return (len(name) > 2 and
            name[0] == name[-1] == '_' and
            name[1:2] != '_' and
            name[-2:-1] != '_')


class EnumDict(dict):
    """
    A copy of enum._EnumDict from Python 3.6 that we are allowed to access and
    doesn't vanish in Python 3.9.

    Track enum member order and ensure member names are not reused.

    EnumMeta will use the names found in self._member_names as the
    enumeration member names.
    """
    def __init__(self):
        super().__init__()
        self._member_names = []
        self._last_values = []
        self._ignore = []
        self._auto_called = False

    def __setitem__(self, key, value):
        """Changes anything not dundered or not a descriptor.

        If an enum member name is used twice, an error is raised; duplicate
        values are not checked for.

        Single underscore (sunder) names are reserved.

        """
        if _is_sunder(key):
            if key not in (
                    '_order_', '_create_pseudo_member_',
                    '_generate_next_value_', '_missing_', '_ignore_',
                    ):
                raise ValueError('_names_ are reserved for future Enum use')
            if key == '_generate_next_value_':
                # check if members already defined as auto()
                if self._auto_called:
                    raise TypeError(
                        "_generate_next_value_ must be defined before members")
                setattr(self, '_generate_next_value', value)
            elif key == '_ignore_':
                if isinstance(value, str):
                    value = value.replace(',', ' ').split()
                else:
                    value = list(value)
                self._ignore = value
                already = set(value) & set(self._member_names)
                if already:
                    raise ValueError(
                        '_ignore_ cannot specify already set names: %r' %
                        (already, )
                    )
        elif _is_dunder(key):
            if key == '__order__':
                key = '_order_'
        elif key in self._member_names:
            # descriptor overwriting an enum?
            raise TypeError('Attempted to reuse key: %r' % key)
        elif key in self._ignore:
            pass
        elif not _is_descriptor(value):
            if key in self:
                # enum overwriting a descriptor?
                raise TypeError('%r already defined as: %r' % (key, self[key]))
            if isinstance(value, _Auto):
                self._auto_called = True
                if value.value == _auto_null:
                    # noinspection PyUnresolvedReferences
                    value.value = self._generate_next_value(
                        key, 1, len(self._member_names), self._last_values[:])
                value = value.value
            self._member_names.append(key)
            self._last_values.append(value)
        super().__setitem__(key, value)


# -----------------------------------------------------------------------------
# AutoStrEnum
# -----------------------------------------------------------------------------

class AutoStrEnumMeta(EnumMeta):
    # noinspection PyInitNewSignature
    def __new__(mcs, cls, bases, oldclassdict):
        """
        Scan through ``oldclassdict`` and convert any value that is a plain
        tuple into a ``str`` of the name instead.
        """
        newclassdict = EnumDict()
        for k, v in oldclassdict.items():
            if v == ():
                v = k
            newclassdict[k] = v
        return super().__new__(mcs, cls, bases, newclassdict)


class AutoStrEnum(str,
                  StrEnum,  # was Enum,
                  metaclass=AutoStrEnumMeta):
    """
    Base class for ``name=value`` ``str`` enums.

    Example:

    .. code-block:: python

        class Animal(AutoStrEnum):
            horse = ()
            dog = ()
            whale = ()

        print(Animal.horse)
        print(Animal.horse == 'horse')
        print(Animal.horse.name, Animal.horse.value)

    See
    https://stackoverflow.com/questions/32214614/automatically-setting-an-enum-members-value-to-its-name/32215467
    and then inherit from :class:`StrEnum` rather than :class:`Enum`.

    """  # noqa
    pass


# -----------------------------------------------------------------------------
# LowerCaseAutoStrEnumMeta
# -----------------------------------------------------------------------------

class LowerCaseAutoStrEnumMeta(EnumMeta):
    # noinspection PyInitNewSignature
    def __new__(mcs, cls, bases, oldclassdict):
        """
        Scan through ``oldclassdict`` and convert any value that is a plain
        tuple into a ``str`` of the name instead.
        """
        newclassdict = EnumDict()
        for k, v in oldclassdict.items():
            if v == ():
                v = k.lower()
            if v in newclassdict.keys():
                raise ValueError(f"Duplicate value caused by key {k}")
            newclassdict[k] = v
        return super().__new__(mcs, cls, bases, newclassdict)


class LowerCaseAutoStrEnum(str, StrEnum, metaclass=LowerCaseAutoStrEnumMeta):
    """
    Base class for ``name=value`` ``str`` enums, forcing lower-case values.

    Example:

    .. code-block:: python

        class AnimalLC(LowerCaseAutoStrEnum):
            Horse = ()
            Dog = ()
            Whale = ()

        print(AnimalLC.Horse)
        print(AnimalLC.Horse == 'horse')
        print(AnimalLC.Horse.name, AnimalLC.Horse.value)

    """
    pass


# -----------------------------------------------------------------------------
# AutoNumberEnum
# -----------------------------------------------------------------------------

class AutoNumberEnum(Enum):
    """
    As per https://docs.python.org/3/library/enum.html (in which, called
    AutoNumber).

    Usage:

    .. code-block:: python

        class Color(AutoNumberEnum):
            red = ()
            green = ()
            blue = ()

        Color.green.value == 2  # True
    """
    def __new__(cls):
        value = len(cls.__members__) + 1  # will be numbered from 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


# -----------------------------------------------------------------------------
# AutoNumberObject
# -----------------------------------------------------------------------------

class AutoNumberObjectMetaClass(type):
    @classmethod
    def __prepare__(mcs, name, bases):  # mcs: was metaclass
        """
        Called when AutoEnum (below) is defined, prior to ``__new__``, with:

        .. code-block:: python

            name = 'AutoEnum'
            bases = ()
        """
        # print("__prepare__: name={}, bases={}".format(
        #     repr(name), repr(bases)))
        return collections.defaultdict(itertools.count().__next__)

    # noinspection PyInitNewSignature
    def __new__(mcs, name, bases, classdict):  # mcs: was cls
        """
        Called when AutoEnum (below) is defined, with:

        .. code-block:: python

            name = 'AutoEnum'
            bases = ()
            classdict = defaultdict(<method-wrapper '__next__' of itertools.count
                    object at 0x7f7d8fc5f648>,
                {
                    '__doc__': '... a docstring... ',
                    '__qualname__': 'AutoEnum',
                    '__name__': 0,
                    '__module__': 0
                }
            )
        """  # noqa
        # print("__new__: name={}, bases={}, classdict={}".format(
        #     repr(name), repr(bases), repr(classdict)))
        cls = type.__new__(mcs, name, bases, dict(classdict))
        return cls  # cls: was result


class AutoNumberObject(metaclass=AutoNumberObjectMetaClass):
    """
    From comment by Duncan Booth at
    https://www.acooke.org/cute/Pythonssad0.html, with trivial rename.

    Usage:

    .. code-block:: python

        class MyThing(AutoNumberObject):
            a
            b

        MyThing.a
        # 1
        MyThing.b
        # 2
    """
    pass


# -----------------------------------------------------------------------------
# LowerCaseAutoStringObject
# -----------------------------------------------------------------------------
# RNC. We need a defaultdict that does the job...
# Or similar. But the defaultdict argument function receives no parameters,
# so it can't read the key. Therefore:

class LowerCaseAutoStringObjectMetaClass(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return collections.defaultdict(int)  # start with all values as 0

    # noinspection PyInitNewSignature
    def __new__(mcs, name, bases, classdict):
        for k in classdict.keys():
            if k.startswith('__'):  # e.g. __qualname__, __name__, __module__
                continue
            value = k.lower()
            if value in classdict.values():
                raise ValueError(f"Duplicate value from key: {k}")
            classdict[k] = value
        cls = type.__new__(mcs, name, bases, dict(classdict))
        return cls


class LowerCaseAutoStringObject(metaclass=LowerCaseAutoStringObjectMetaClass):
    """
    Usage:

    .. code-block:: python

        class Wacky(LowerCaseAutoStringObject):
            Thing  # or can use Thing = () to avoid IDE complaints
            OtherThing = ()

        Wacky.Thing  # 'thing'
        Wacky.OtherThing  # 'otherthing'
    """
    pass


# -----------------------------------------------------------------------------
# AutoStringObject
# -----------------------------------------------------------------------------
# RNC. We need a defaultdict that does the job...
# Or similar. But the defaultdict argument function receives no parameters,
# so it can't read the key. Therefore:

class AutoStringObjectMetaClass(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return collections.defaultdict(int)

    # noinspection PyInitNewSignature
    def __new__(mcs, name, bases, classdict):
        for k in classdict.keys():
            if k.startswith('__'):  # e.g. __qualname__, __name__, __module__
                continue
            classdict[k] = k
        cls = type.__new__(mcs, name, bases, dict(classdict))
        return cls


class AutoStringObject(metaclass=AutoStringObjectMetaClass):
    """
    Usage:

    .. code-block:: python

        class Fish(AutoStringObject):
            Thing
            Blah

        Fish.Thing  # 'Thing'
    """
    pass


# =============================================================================
# enum: TOO OLD; NAME CLASH; DEPRECATED/REMOVED
# =============================================================================

# def enum(**enums: Any) -> Enum:
#     """Enum support, as at https://stackoverflow.com/questions/36932"""
#     return type('Enum', (), enums)


# =============================================================================
# AttrDict: DEPRECATED
# =============================================================================

class AttrDict(dict):
    """
    Dictionary with attribute access; see
    https://stackoverflow.com/questions/4984647
    """
    def __init__(self, *args, **kwargs) -> None:
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


# =============================================================================
# OrderedNamespace
# =============================================================================
# for attrdict itself: use the attrdict package

class OrderedNamespace(object):
    """
    As per https://stackoverflow.com/questions/455059, modified for
    ``__init__``.
    """
    def __init__(self, *args):
        super().__setattr__('_odict', OrderedDict(*args))

    def __getattr__(self, key):
        odict = super().__getattribute__('_odict')
        if key in odict:
            return odict[key]
        return super().__getattribute__(key)

    def __setattr__(self, key, val):
        self._odict[key] = val

    @property
    def __dict__(self):
        return self._odict

    def __setstate__(self, state):  # Support copy.copy
        super().__setattr__('_odict', OrderedDict())
        self._odict.update(state)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)

    # Plus more (RNC):
    def items(self):
        return self.__dict__.items()

    def __repr__(self):
        return ordered_repr(self, self.__dict__.keys())


# =============================================================================
# keys_descriptions_from_enum
# =============================================================================

def keys_descriptions_from_enum(
        enum: Type[Enum],
        sort_keys: bool = False,
        keys_to_lower: bool = False,
        keys_to_upper: bool = False,
        key_to_description: str = ": ",
        joiner: str = " // ") -> Tuple[List[str], str]:
    """
    From an Enum subclass, return (keys, descriptions_as_formatted_string).
    This is a convenience function used to provide command-line help for
    options involving a choice of enums from an Enum class.
    """
    assert not (keys_to_lower and keys_to_upper)
    keys = [e.name for e in enum]
    if keys_to_lower:
        keys = [k.lower() for k in keys]
    elif keys_to_upper:
        keys = [k.upper() for k in keys]
    if sort_keys:
        keys.sort()
    try:
        descriptions = [
            f"{k}{key_to_description}{enum[k].value}"
            for k in keys
        ]
    except KeyError:
        raise KeyError(
            "You are trying to do case-insensitive lookup with a "
            "case-sensitive Enum. Use a metaclass like "
            "cardinal_pythonlib.enumlike.CaseInsensitiveEnumMeta"
        )
    description_str = joiner.join(descriptions)
    return keys, description_str


# =============================================================================
# EnumLower
# =============================================================================

class CaseInsensitiveEnumMeta(EnumMeta):
    """
    An Enum that permits lookup by a lower-case version of its keys.

    https://stackoverflow.com/questions/42658609/how-to-construct-a-case-insensitive-enum

    Example:

    .. code-block:: python

        from enum import Enum
        from cardinal_pythonlib.enumlike import CaseInsensitiveEnumMeta

        class TestEnum(Enum, metaclass=CaseInsensitiveEnumMeta):
            REDAPPLE = 1
            greenapple = 2
            PineApple = 3

        TestEnum["REDAPPLE"]  # <TestEnum.REDAPPLE: 1>
        TestEnum["redapple"]  # <TestEnum.REDAPPLE: 1>
        TestEnum["greenapple"]  # <TestEnum.greenapple: 2>
        TestEnum["greenappLE"]  # <TestEnum.greenapple: 2>
        TestEnum["PineApple"]  # <TestEnum.PineApple: 3>
        TestEnum["PineApplE"]  # <TestEnum.PineApple: 3>

    """  # noqa
    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            item_lower = item.lower()
            for member in self:
                if member.name.lower() == item_lower:
                    return member
        return super().__getitem__(item)
