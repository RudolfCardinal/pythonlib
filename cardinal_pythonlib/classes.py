#!/usr/bin/env python
# cardinal_pythonlib/classes.py

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

**Functions to help work with Python classes.**

"""

from typing import Generator, List, Type, TypeVar


# =============================================================================
# Does a derived class implement a method?
# =============================================================================

"""
http://stackoverflow.com/questions/1776994
https://docs.python.org/3/library/inspect.html
https://github.com/edoburu/django-fluent-contents/issues/43
https://bytes.com/topic/python/answers/843424-python-2-6-3-0-determining-if-method-inherited  # noqa
https://docs.python.org/3/reference/datamodel.html

In Python 2, you can do this:
    return derived_method.__func__ != base_method.__func__
In Python 3.4:
    ...

class Base(object):
    def one():
        print("base one")
    def two():
        print("base two")


class Derived(Base):
    def two():
        print("derived two")


Derived.two.__dir__()  # not all versions of Python


derived_class_implements_method(Derived, Base, 'one')  # should be False
derived_class_implements_method(Derived, Base, 'two')  # should be True
derived_class_implements_method(Derived, Base, 'three')  # should be False

"""

T1 = TypeVar('T1')
T2 = TypeVar('T2')


def derived_class_implements_method(derived: Type[T1],
                                    base: Type[T2],
                                    method_name: str) -> bool:
    """
    Does a derived class implement a method (and not just inherit a base
    class's version)?

    Args:
        derived: a derived class
        base: a base class
        method_name: the name of a method

    Returns:
        whether the derived class method is (a) present, and (b) different to
        the base class's version of the same method

    Note: if C derives from B derives from A, then a check on C versus A will
    succeed if C implements the method, or if C inherits it from B but B has
    re-implemented it compared to A.

    """
    derived_method = getattr(derived, method_name, None)
    if derived_method is None:
        return False
    base_method = getattr(base, method_name, None)
    # if six.PY2:
    #     return derived_method.__func__ != base_method.__func__
    # else:
    #     return derived_method is not base_method
    return derived_method is not base_method


# =============================================================================
# Subclasses
# =============================================================================
# https://stackoverflow.com/questions/3862310/how-can-i-find-all-subclasses-of-a-class-given-its-name  # noqa

def gen_all_subclasses(cls: Type) -> Generator[Type, None, None]:
    """
    Generates all subclasses of a class.

    Args:
        cls: a class

    Yields:
        all subclasses

    """

    for s1 in cls.__subclasses__():
        yield s1
        for s2 in gen_all_subclasses(s1):
            yield s2


def all_subclasses(cls: Type) -> List[Type]:
    """
    Returns all subclasses of a class.

    Args:
        cls: a class

    Returns:
        a list of all subclasses

    """
    return list(gen_all_subclasses(cls))


# =============================================================================
# Class properties
# =============================================================================

class ClassProperty(property):
    """
    One way to mark a function as a class property (logically, a combination of
    ``@classmethod`` and ``@property``).

    See
    https://stackoverflow.com/questions/128573/using-property-on-classmethods.

    However, in practice we use :class:`classproperty`, a slightly different
    version.
    """
    # https://stackoverflow.com/questions/128573/using-property-on-classmethods
    # noinspection PyMethodOverriding
    def __get__(self, cls, owner):
        # noinspection PyUnresolvedReferences
        return self.fget.__get__(None, owner)()


# noinspection PyPep8Naming
class classproperty(object):
    """
    Decorator to mark a function as a class property (logically, a combination
    of ``@classmethod`` and ``@property``).

    See
    https://stackoverflow.com/questions/128573/using-property-on-classmethods
    """
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)
