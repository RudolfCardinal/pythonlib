#!/usr/bin/env python
# -*- encoding: utf8 -*-

"""Support functions to do with the core language.

Author: Rudolf Cardinal (rudolf@pobox.com)
Created: 2013
Last update: 24 Sep 2015

Copyright/licensing:

    Copyright (C) 2013-2015 Rudolf Cardinal (rudolf@pobox.com).

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

import collections
# noinspection PyProtectedMember
from enum import EnumMeta, Enum, _EnumDict
import importlib
import itertools
import logging
import pkgutil
from typing import Any, Dict, Iterable, List, Optional, Union
from types import ModuleType

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
# log.setLevel(logging.DEBUG)

# =============================================================================
# Enum-based classes
# =============================================================================
"""
https://docs.python.org/3/library/enum.html

The good things about enums are:
- they are immutable
- they are "class-like", not "instance-like"
- they can be accessed via attribute (like an object) or item (like a dict):
- you can add a "@unique" decorator to ensure no two have the same value
- IDEs know about them

AttrDict's disadvantages are:
- more typing / DRY
- IDEs don't know about them

Plain old objects:
- not immutable
- no dictionary access -- though can use getattr()
- but otherwise simpler than enums

LowerCaseAutoStringObject:
- IDEs don't understand their values, so get types wrong


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

        __init__(self) controls the initialization of an instance

"""

# -----------------------------------------------------------------------------
# StrEnum:
# - makes str(myenum.x) give str(myenum.x.value)
# - adds a lookup function (from a string literal)
# - adds ordering by value
# -----------------------------------------------------------------------------

STR_ENUM_FWD_REF = "StrEnum"
# class name forward reference for type checker:
# http://mypy.readthedocs.io/en/latest/kinds_of_types.html
# ... but also: a variable (rather than a string literal) stops PyCharm giving
# the curious error "PEP 8: no newline at end of file" and pointing to the
# type hint string literal.


class StrEnum(Enum):
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
        raise ValueError("Value {} not found in enum class {}".format(
            repr(value), cls.__name__))

    def __lt__(self, other: STR_ENUM_FWD_REF) -> bool:
        return str(self) < str(other)


# -----------------------------------------------------------------------------
# AutoStrEnum
# -----------------------------------------------------------------------------
# http://stackoverflow.com/questions/32214614/automatically-setting-an-enum-members-value-to-its-name/32215467
# ... and then inherit from StrEnum rather than Enum

class AutoStrEnumMeta(EnumMeta):
    def __new__(mcs, cls, bases, oldclassdict):
        """
        Scan through `oldclassdict` and convert any value that is a plain tuple
        into a `str` of the name instead
        """
        newclassdict = _EnumDict()
        for k, v in oldclassdict.items():
            if v == ():
                v = k
            newclassdict[k] = v
        return super().__new__(mcs, cls, bases, newclassdict)


class AutoStrEnum(str,
                  StrEnum,  # was Enum,
                  metaclass=AutoStrEnumMeta):
    """base class for name=value str enums"""


# class Animal(AutoStrEnum):
#     horse = ()
#     dog = ()
#     whale = ()
#
# print(Animal.horse)
# print(Animal.horse == 'horse')
# print(Animal.horse.name, Animal.horse.value)


# -----------------------------------------------------------------------------
# AutoStrEnum
# -----------------------------------------------------------------------------
# http://stackoverflow.com/questions/32214614/automatically-setting-an-enum-members-value-to-its-name/32215467
# ... and then inherit from StrEnum rather than Enum

class LowerCaseAutoStrEnumMeta(EnumMeta):
    def __new__(mcs, cls, bases, oldclassdict):
        """
        Scan through `oldclassdict` and convert any value that is a plain tuple
        into a `str` of the name instead
        """
        newclassdict = _EnumDict()
        for k, v in oldclassdict.items():
            if v == ():
                v = k.lower()
            if v in newclassdict.keys():
                raise ValueError("Duplicate value caused by key {}".format(k))
            newclassdict[k] = v
        return super().__new__(mcs, cls, bases, newclassdict)


class LowerCaseAutoStrEnum(str, StrEnum, metaclass=LowerCaseAutoStrEnumMeta):
    """base class for name=value str enums, forcing lower-case values"""


# class AnimalLC(LowerCaseAutoStrEnum):
#     Horse = ()
#     Dog = ()
#     Whale = ()
#
# print(AnimalLC.Horse)
# print(AnimalLC.Horse == 'horse')
# print(AnimalLC.Horse.name, AnimalLC.Horse.value)


# -----------------------------------------------------------------------------
# AutoNumberEnum
# -----------------------------------------------------------------------------

class AutoNumberEnum(Enum):
    """
    https://docs.python.org/3/library/enum.html (in which, called AutoNumber)
    Usage:
        class Color(AutoNumberEnum):
            red = ()
            green = ()
            blue = ()

        Color.green.value == 2
        # True
    """
    def __new__(cls):
        value = len(cls.__members__) + 1  # will be numbered from 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


"""
class Color(AutoNumberEnum):
    red = ()
    green = ()
    blue = ()
"""


# -----------------------------------------------------------------------------
# AutoNumberObject
# -----------------------------------------------------------------------------
# From comment by Duncan Booth at
# http://www.acooke.org/cute/Pythonssad0.html
# ... with trivial rename

class AutoNumberObjectMetaClass(type):
    @classmethod
    def __prepare__(mcs, name, bases):  # mcs: was metaclass
        """
        Called when AutoEnum (below) is defined, prior to __new__, with:
        name = 'AutoEnum'
        bases = ()
        """
        # print("__prepare__: name={}, bases={}".format(
        #     repr(name), repr(bases)))
        return collections.defaultdict(itertools.count().__next__)

    def __new__(mcs, name, bases, classdict):  # mcs: was cls
        """
        Called when AutoEnum (below) is defined, with:

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
        """
        # print("__new__: name={}, bases={}, classdict={}".format(
        #     repr(name), repr(bases), repr(classdict)))
        cls = type.__new__(mcs, name, bases, dict(classdict))
        return cls  # cls: was result


class AutoNumberObject(metaclass=AutoNumberObjectMetaClass):
    """
    Usage:
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
# RNC. We need a defaultdict that does the job...
# Or similar. But the defaultdict argument function receives no parameters,
# so it can't read the key. Therefore:

class LowerCaseAutoStringObjectMetaClass(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return collections.defaultdict(int)  # start with all values as 0

    def __new__(mcs, name, bases, classdict):
        for k in classdict.keys():
            if k.startswith('__'):  # e.g. __qualname__, __name__, __module__
                continue
            value = k.lower()
            if value in classdict.values():
                raise ValueError("Duplicate value from key: {}".format(k))
            classdict[k] = value
        cls = type.__new__(mcs, name, bases, dict(classdict))
        return cls


class LowerCaseAutoStringObject(metaclass=LowerCaseAutoStringObjectMetaClass):
    """
    Usage:
        class Wacky(LowerCaseAutoStringObject):
            Thing  # or can use Thing = () to avoid IDE complaints
            OtherThing = ()

        Wacky.Thing
        # 'thing'
        Wacky.OtherThing
        # 'otherthing'
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
        class Fish(AutoStringObject):
            Thing
            Blah

        Fish.Thing
        # 'Thing'
    """
    pass


# =============================================================================
# enum: TOO OLD; NAME CLASH; DEPRECATED/REMOVED
# =============================================================================

# def enum(**enums: Any) -> Enum:
#     """Enum support, as at http://stackoverflow.com/questions/36932"""
#     return type('Enum', (), enums)


# =============================================================================
# AttrDict: DEPRECATED
# =============================================================================

class AttrDict(dict):
    # http://stackoverflow.com/questions/4984647
    def __init__(self, *args, **kwargs) -> None:
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


# =============================================================================
# Other dictionary operations
# =============================================================================

def merge_dicts(*dict_args: Dict) -> Dict:
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    # http://stackoverflow.com/questions/38987
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


# =============================================================================
# Helper functions
# =============================================================================

def convert_to_bool(x: Any, default: bool = None) -> bool:
    if isinstance(x, bool):
        return x
    if not x:  # None, zero, blank string...
        return default
    try:
        return int(x) != 0
    except (TypeError, ValueError):
        pass
    try:
        return float(x) != 0
    except (TypeError, ValueError):
        pass
    if not isinstance(x, str):
        raise Exception("Unknown thing being converted to bool: {}".format(x))
    x = x.upper()
    if x in ["Y", "YES", "T", "TRUE"]:
        return True
    if x in ["N", "NO", "F", "FALSE"]:
        return False
    raise Exception("Unknown thing being converted to bool: {}".format(x))


def convert_attrs_to_bool(obj: Any,
                          attrs: Iterable[str],
                          default: bool = None) -> None:
    for a in attrs:
        setattr(obj, a, convert_to_bool(getattr(obj, a), default=default))


def convert_attrs_to_uppercase(obj: Any, attrs: Iterable[str]) -> None:
    for a in attrs:
        value = getattr(obj, a)
        if value is None:
            continue
        setattr(obj, a, value.upper())


def convert_attrs_to_lowercase(obj: Any, attrs: Iterable[str]) -> None:
    for a in attrs:
        value = getattr(obj, a)
        if value is None:
            continue
        setattr(obj, a, value.lower())


def convert_to_int(x: Any, default: int = None) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def convert_attrs_to_int(obj: Any,
                         attrs: Iterable[str],
                         default: int = None) -> None:
    for a in attrs:
        value = convert_to_int(getattr(obj, a), default=default)
        setattr(obj, a, value)


def raise_if_attr_blank(obj: Any, attrs: Iterable[str]) -> None:
    for a in attrs:
        value = getattr(obj, a)
        if value is None or value is "":
            raise Exception("Blank attribute: {}".format(a))


def count_bool(blist: Iterable[Any]) -> int:
    return sum([1 if x else 0 for x in blist])


def chunks(l: List[Any], n: int) -> Iterable[List[Any]]:
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]


def is_integer(s: Any) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


# =============================================================================
# Module management
# =============================================================================

def import_submodules(package: Union[str, ModuleType],
                      base_package_for_relative_import: str = None,
                      recursive: bool = True) -> Dict[str, ModuleType]:
    # http://stackoverflow.com/questions/3365740/how-to-import-all-submodules
    """ Import all submodules of a module, recursively, including subpackages

    :param package: package (name or actual module)
    :param base_package_for_relative_import: path to prepend?
    :param recursive: import submodules too
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        package = importlib.import_module(package,
                                          base_package_for_relative_import)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        log.debug("importing: {}".format(full_name))
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results

# Note slightly nastier way: e.g.
#   # Task imports: everything in "tasks" directory
#   task_modules = glob.glob(os.path.dirname(__file__) + "/tasks/*.py")
#   task_modules = [os.path.basename(f)[:-3] for f in task_modules]
#   for tm in task_modules:
#       __import__(tm, locals(), globals())
