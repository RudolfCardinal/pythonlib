#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/dialect.py

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

**Helper functions relating to SQLAlchemy SQL dialects.**

"""

from typing import Union

from sqlalchemy.engine import Connection, create_engine, Engine
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.compiler import IdentifierPreparer, SQLCompiler


# =============================================================================
# Constants
# =============================================================================


class SqlaDialectName(object):
    """
    Dialect names used by SQLAlchemy.
    """

    # SQLAlchemy itself:

    FIREBIRD = "firebird"
    MYSQL = "mysql"
    MSSQL = "mssql"
    ORACLE = "oracle"
    POSTGRES = "postgresql"
    SQLITE = "sqlite"
    SQLSERVER = MSSQL  # synonym
    SYBASE = "sybase"

    # Additional third-party dialects:
    # - https://docs.sqlalchemy.org/en/20/dialects/
    # Interface:
    # - https://docs.sqlalchemy.org/en/20/core/internals.html#sqlalchemy.engine.Dialect  # noqa: E501

    DATABRICKS = "databricks"
    # ... https://github.com/databricks/databricks-sqlalchemy
    # ... https://docs.databricks.com/en/sql/language-manual/index.html


ALL_SQLA_DIALECTS = list(
    set(
        [
            getattr(SqlaDialectName, k)
            for k in dir(SqlaDialectName)
            if not k.startswith("_")
        ]
    )
)


# =============================================================================
# Dialect stuff
# =============================================================================


def get_dialect(
    mixed: Union[Engine, Dialect, Session, SQLCompiler]
) -> Union[Dialect, type(Dialect)]:
    """
    Finds the SQLAlchemy dialect in use.

    Args:
        mixed:
            An SQLAlchemy engine, bound session, SQLCompiler, or Dialect
            object.

    Returns: the SQLAlchemy :class:`Dialect` being used

    """
    if isinstance(mixed, Dialect):
        return mixed
    elif isinstance(mixed, Engine):
        return mixed.dialect
    elif isinstance(mixed, Session):
        if mixed.bind is None:
            raise ValueError("get_dialect: parameter is an unbound session")
        bind = mixed.bind
        assert isinstance(bind, (Engine, Connection))
        return bind.dialect
    elif isinstance(mixed, SQLCompiler):
        return mixed.dialect
    else:
        raise ValueError(
            f"get_dialect: 'mixed' parameter of wrong type: {mixed!r}"
        )


def get_dialect_name(
    mixed: Union[Engine, Dialect, Session, SQLCompiler]
) -> str:
    """
    Finds the name of the SQLAlchemy dialect in use.

    Args:
        mixed:
            An SQLAlchemy engine, bound session, SQLCompiler, or Dialect
            object.

    Returns: the SQLAlchemy dialect name being used
    """
    dialect = get_dialect(mixed)
    # noinspection PyUnresolvedReferences
    return dialect.name


def get_preparer(
    mixed: Union[Engine, Dialect, Session, SQLCompiler]
) -> IdentifierPreparer:
    """
    Returns the SQLAlchemy :class:`IdentifierPreparer` in use for the dialect
    being used.

    Args:
        mixed:
            An SQLAlchemy engine, bound session, SQLCompiler, or Dialect
            object.

    Returns: an :class:`IdentifierPreparer`

    """
    dialect = get_dialect(mixed)
    # noinspection PyUnresolvedReferences
    return dialect.preparer(dialect)  # type: IdentifierPreparer


def quote_identifier(
    identifier: str, mixed: Union[Engine, Dialect, Session, SQLCompiler]
) -> str:
    """
    Converts an SQL identifier to a quoted version, via the SQL dialect in
    use.

    Args:
        identifier: the identifier to be quoted
        mixed:
            An SQLAlchemy engine, bound session, SQLCompiler, or Dialect
            object.

    Returns:
        the quoted identifier

    """
    # See also http://sqlalchemy-utils.readthedocs.io/en/latest/_modules/sqlalchemy_utils/functions/orm.html  # noqa: E501
    return get_preparer(mixed).quote(identifier)


def get_dialect_from_name(dialect_name: str) -> Dialect:
    """
    Creates a Dialect. Not very elegant.
    """

    # noinspection PyUnusedLocal
    def null_executor(querysql, *multiparams, **params):
        pass

    engine = create_engine(
        f"{dialect_name}://",
        strategy="mock",
        executor=null_executor,
        future=True,
    )
    return engine.dialect
