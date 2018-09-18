#!/usr/bin/env python
# cardinal_pythonlib/metaclasses.py

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

**Support functions to do with metaclasses. IGNORE; NOT WORKING PROPERLY.**

"""

from typing import Any, Dict, Tuple, Type


class CooperativeMeta(type):
    """
    The idea is to use this as the metaclass for a class ``Derived`` that
    inherits from bases ``BaseOne``, ``BaseTwo``, ..., whose metaclasses are
    not of the same type.

    This should avoid the error:
    
    .. code-block:: none

        TypeError: metaclass conflict: the metaclass of a derived class must
        be a (non-strict) subclass of the metaclasses of all its bases

    Code from:
    https://stackoverflow.com/questions/6557407/triple-inheritance-causes-metaclass-conflict-sometimes.

    See also:
    http://code.activestate.com/recipes/204197-solving-the-metaclass-conflict/.

    HOWEVER, it's not actually working. Does Python 3 have stricter checking
    than Python 2?

    See also
    https://blog.ionelmc.ro/2015/02/09/understanding-python-metaclasses/.
    """  # noqa
    def __new__(mcs: Type,
                name: str,
                bases: Tuple[Type, ...],
                members: Dict[str, Any]) -> Type:
        # collect up the metaclasses
        metas = [type(base) for base in bases]

        # prune repeated or conflicting entries
        metas = [meta for index, meta in enumerate(metas)
                 if not [later for later in metas[index + 1:]
                         if issubclass(later, meta)]]

        # whip up the actual combined meta class; derive off all of these
        meta = type(name, tuple(metas), dict(combined_metas=metas))

        # make the actual object
        return meta(name, bases, members)

    # noinspection PyMissingConstructor
    def __init__(cls: Type,
                 name: str,
                 bases: Tuple[Type, ...],
                 members: Dict[str, Any]) -> None:
        # noinspection PyUnresolvedReferences
        for meta in cls.combined_metas:
            meta.__init__(cls, name, bases, members)


class DebuggingCooperativeMeta(type):
    """
    ``CooperativeMeta``, but with :func:`print` output.
    Still not working.
    """
    def __new__(mcs: Type,
                name: str,
                bases: Tuple[Type, ...],
                members: Dict[str, Any]) -> Type:
        metas = [type(base) for base in bases]
        metas = [meta for index, meta in enumerate(metas)
                 if not [later for later in metas[index + 1:]
                         if issubclass(later, meta)]]
        meta = type(name, tuple(metas), dict(combined_metas=metas))
        obj = meta(name, bases, members)

        print("DebuggingCooperativeMeta.__new__: bases = {}".format(repr(bases)))  # noqa
        print("DebuggingCooperativeMeta.__new__: metas = {}".format(repr(metas)))  # noqa
        print("DebuggingCooperativeMeta.__new__: meta = {}".format(repr(meta)))
        print("DebuggingCooperativeMeta.__new__: obj = {}".format(repr(obj)))

        # make the actual object
        return obj

    # noinspection PyMissingConstructor
    def __init__(cls: Type,
                 name: str,
                 bases: Tuple[Type, ...],
                 members: Dict[str, Any]) -> None:
        # noinspection PyUnresolvedReferences
        for meta in cls.combined_metas:
            print(
                "DebuggingCooperativeMeta.__init__: calling {meta}.__init__("
                "{name}, {bases}, {members}".format(
                    meta=meta.__name__,
                    name=repr(name),
                    bases=repr(bases),
                    members=repr(members)
                )
            )
            meta.__init__(cls, name, bases, members)


TEST_CODE_SHOULD_FAIL = """

class MetaA(type):
    pass

class MetaB(type):
    pass

class A(metaclass=MetaA):
    pass
    
class B(metaclass=MetaB):
    pass
    
class Fixed(A, B):
    pass

"""

TEST_CODE_SHOULD_SUCCEED_BUT_DOES_NOT = """

from cardinal_pythonlib.metaclasses import CooperativeMeta

class MetaA(type):
    pass

class MetaB(type):
    pass

class A(metaclass=MetaA):
    pass
    
class B(metaclass=MetaB):
    pass
    
class Fixed(A, B, metaclass=CooperativeMeta):
    pass

"""
