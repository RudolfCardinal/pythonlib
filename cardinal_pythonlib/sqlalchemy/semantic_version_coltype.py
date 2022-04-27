#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/semantic_version_coltype.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

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

**SQLAlchemy column type to hold semantic versions.**

- See https://semver.org/

"""

# =============================================================================
# Imports
# =============================================================================

from typing import Any, Callable, Optional

from semantic_version import Version

from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.sqltypes import String
from sqlalchemy.sql.type_api import TypeDecorator


# =============================================================================
# Semantic version column type
# =============================================================================


def make_semantic_version(value: Any) -> Optional[Version]:
    """
    Returns a :class:`semantic_version.Version` from its input or raises
    :exc:`ValueError`. If the input is ``None``, returns Version("0.0.0").

    This is the default function to create a :class:`semantic_version.Version`
    from a string (or NULL/``None`` value) retrieved from the database.
    """
    if value is None:
        return None
    return Version(value)  # may raise ValueError


MakeSemanticVersionFnType = Callable[[Any], Optional[Version]]


class SemanticVersionColType(TypeDecorator):
    """
    Stores semantic versions in the database.
    Uses :class:`semantic_version.Version` on the Python side.
    A NULL in the database will be treated as version 0.0.0.
    """

    impl = String(length=147)  # https://github.com/mojombo/semver/issues/79

    _coltype_name = "SemanticVersionColType"

    def __init__(
        self,
        *args,
        make_version: MakeSemanticVersionFnType = make_semantic_version,
        **kwargs
    ) -> None:
        """
        Args:
            *args:
                Arguments to the :class:`Column` constructor.
            make_version:
                Function that takes an arbitrary value (which will be a string
                or ``None`` value from the database) and returns a
                :class:`semantic_version.Version` object (or ``None``).
                A default function is supplied, but you can override this to
                use your own.
            **kwargs:
                Arguments to the :class:`Column` constructor.
        """
        self.make_version = make_version
        super().__init__(*args, **kwargs)

    @property
    def python_type(self) -> type:
        """
        The Python type of the object.
        """
        return Version

    def process_bind_param(
        self, value: Optional[Version], dialect: Dialect
    ) -> Optional[str]:
        """
        Convert parameters on the way from Python to the database.
        """
        return str(value) if value is not None else None

    def process_literal_param(
        self, value: Optional[Version], dialect: Dialect
    ) -> Optional[str]:
        """
        Convert literals on the way from Python to the database.
        """
        return str(value) if value is not None else None

    def process_result_value(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[Version]:
        """
        Convert things on the way from the database to Python.
        """
        return self.make_version(value)

    '''
    # noinspection PyPep8Naming
    class comparator_factory(TypeDecorator.Comparator):
        """
        Process SQL for when we are comparing our column, in the database,
        to something else.

        See https://docs.sqlalchemy.org/en/13/core/type_api.html#sqlalchemy.types.TypeEngine.comparator_factory.

        .. warning::

            I'm not sure this is either (a) correct or (b) used; it may
            produce a string comparison of e.g. ``14.0.0`` versus ``2.0.0``,
            which will be alphabetical and therefore wrong.
            Disabled on 2019-04-28.

        """  # noqa

        def operate(self, op, *other, **kwargs):
            assert len(other) == 1
            assert not kwargs
            other = other[0]
            if isinstance(other, Version):
                processed_other = str(Version)
            else:
                processed_other = other
            return op(self.expr, processed_other)

        def reverse_operate(self, op, *other, **kwargs):
            assert False, "I don't think this is ever being called"
    '''
