#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/arrow_types.py

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

**SQLAlchemy type to hold a Python Arrow date/time. Uses a DATETIME or similar
type in the database.**

"""

import datetime
from typing import Any, Iterable, Optional

import arrow
import sqlalchemy.dialects.mssql
import sqlalchemy.dialects.mysql
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.sql.type_api import TypeDecorator, TypeEngine

from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName


# =============================================================================
# ArrowType that uses fractional second support in MySQL
# =============================================================================

class ArrowMicrosecondType(TypeDecorator):
    """
    Based on ArrowType from SQLAlchemy-Utils, but copes with fractional seconds
    under MySQL 5.6.4+.
    """
    impl = DateTime
    # RNC: For MySQL, need to use sqlalchemy.dialects.mysql.DATETIME(fsp=6);
    # see load_dialect_impl() below.

    def __init__(self, *args, **kwargs) -> None:
        if not arrow:
            raise AssertionError(
                "'arrow' package is required to use 'ArrowMicrosecondType'")
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect: DefaultDialect) -> TypeEngine:  # RNC
        if dialect.name == SqlaDialectName.MYSQL:
            return dialect.type_descriptor(
                sqlalchemy.dialects.mysql.DATETIME(fsp=6))
        elif dialect.name == SqlaDialectName.MSSQL:  # Microsoft SQL Server
            return dialect.type_descriptor(sqlalchemy.dialects.mssql.DATETIME2)
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(
            self, value: Any,
            dialect: DefaultDialect) -> Optional[datetime.datetime]:
        if value:
            return self._coerce(value).to('UTC').naive
            # RNC: unfortunately... can't store and retrieve timezone, see docs
        return value

    def process_result_value(self, value: Any,
                             dialect: DefaultDialect) -> Optional[arrow.Arrow]:
        if value:
            return arrow.get(value)
        return value

    def process_literal_param(self, value: Any, dialect: DefaultDialect) -> str:
        return str(value)

    # noinspection PyMethodMayBeStatic
    def _coerce(self, value: Any) -> Optional[arrow.Arrow]:
        if value is None:
            return None
        elif isinstance(value, str):  # RNC
            value = arrow.get(value)
        elif isinstance(value, Iterable):
            value = arrow.get(*value)
        elif isinstance(value, datetime.datetime):  # RNC trivial change
            value = arrow.get(value)
        return value

    # noinspection PyUnusedLocal
    def coercion_listener(self, target, value, oldvalue,
                          initiator) -> Optional[arrow.Arrow]:
        return self._coerce(value)

    @property
    def python_type(self) -> type:
        # noinspection PyUnresolvedReferences
        return self.impl.type.python_type
