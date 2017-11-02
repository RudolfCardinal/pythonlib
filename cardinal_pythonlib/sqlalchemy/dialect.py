#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/dialect.py

"""
===============================================================================
    Copyright (C) 2009-2017 Rudolf Cardinal (rudolf@pobox.com).

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

from typing import Union

from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.compiler import IdentifierPreparer, SQLCompiler


# =============================================================================
# Constants
# =============================================================================

class SqlaDialectName(object):
    """
    Dialect names used by SQLAlchemy.
    """
    FIREBIRD = "firebird"
    MYSQL = 'mysql'
    MSSQL = 'mssql'
    ORACLE = 'oracle'
    POSTGRES = 'postgresql'
    SQLITE = 'sqlite'
    SQLSERVER = MSSQL  # synonym
    SYBASE = 'sybase'


ALL_SQLA_DIALECTS = list(set(
    [getattr(SqlaDialectName, k)
     for k in dir(SqlaDialectName) if not k.startswith("_")]
))


# =============================================================================
# Dialect stuff
# =============================================================================

def get_dialect(mixed: Union[SQLCompiler, Engine, Dialect]) -> Dialect:
    if isinstance(mixed, Dialect):
        return mixed
    elif isinstance(mixed, Engine):
        return mixed.dialect
    elif isinstance(mixed, SQLCompiler):
        return mixed.dialect
    else:
        raise ValueError("get_dialect: 'mixed' parameter of wrong type")


def get_dialect_name(mixed: Union[SQLCompiler, Engine, Dialect]) -> str:
    dialect = get_dialect(mixed)
    # noinspection PyUnresolvedReferences
    return dialect.name


def get_preparer(mixed: Union[SQLCompiler, Engine,
                              Dialect]) -> IdentifierPreparer:
    dialect = get_dialect(mixed)
    # noinspection PyUnresolvedReferences
    return dialect.preparer(dialect)  # type: IdentifierPreparer


def quote_identifier(identifier: str,
                     mixed: Union[SQLCompiler, Engine, Dialect]) -> str:
    # See also http://sqlalchemy-utils.readthedocs.io/en/latest/_modules/sqlalchemy_utils/functions/orm.html  # noqa
    return get_preparer(mixed).quote(identifier)
