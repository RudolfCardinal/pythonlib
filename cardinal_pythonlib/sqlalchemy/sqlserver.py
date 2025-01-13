#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/sqlserver.py

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

**SQLAlchemy functions specific to Microsoft SQL Server.**

"""

from contextlib import contextmanager

from sqlalchemy.engine.base import Engine
from sqlalchemy.orm.session import Session as SqlASession
from sqlalchemy.schema import DDL

from cardinal_pythonlib.sqlalchemy.dialect import (
    quote_identifier,
    SqlaDialectName,
)
from cardinal_pythonlib.sqlalchemy.schema import execute_ddl
from cardinal_pythonlib.sqlalchemy.session import get_engine_from_session


# =============================================================================
# Workarounds for SQL Server "DELETE takes forever" bug
# =============================================================================


def _exec_ddl_if_sqlserver(engine: Engine, sql: str) -> None:
    """
    Execute DDL only if we are running on Microsoft SQL Server.
    """
    ddl = DDL(sql).execute_if(dialect=SqlaDialectName.SQLSERVER)
    execute_ddl(engine, ddl=ddl)


@contextmanager
def if_sqlserver_disable_constraints(
    session: SqlASession, tablename: str
) -> None:
    """
    If we're running under SQL Server, disable constraint checking for the
    specified table while the resource is held.

    Args:
        session: SQLAlchemy :class:`Session`
        tablename: table name

    See
    https://stackoverflow.com/questions/123558/sql-server-2005-t-sql-to-temporarily-disable-a-trigger
    """
    engine = get_engine_from_session(session)
    quoted_tablename = quote_identifier(tablename, engine)
    _exec_ddl_if_sqlserver(
        engine, f"ALTER TABLE {quoted_tablename} NOCHECK CONSTRAINT all"
    )
    yield
    _exec_ddl_if_sqlserver(
        engine,
        f"ALTER TABLE {quoted_tablename} WITH CHECK CHECK CONSTRAINT all",
    )
    # "CHECK CHECK" is correct here.


@contextmanager
def if_sqlserver_disable_triggers(
    session: SqlASession, tablename: str
) -> None:
    """
    If we're running under SQL Server, disable triggers for the specified table
    while the resource is held.

    Args:
        session: SQLAlchemy :class:`Session`
        tablename: table name

    See
    https://stackoverflow.com/questions/123558/sql-server-2005-t-sql-to-temporarily-disable-a-trigger
    """
    engine = get_engine_from_session(session)
    quoted_tablename = quote_identifier(tablename, engine)
    _exec_ddl_if_sqlserver(
        engine, f"ALTER TABLE {quoted_tablename} DISABLE TRIGGER all"
    )
    yield
    _exec_ddl_if_sqlserver(
        engine, f"ALTER TABLE {quoted_tablename} ENABLE TRIGGER all"
    )


@contextmanager
def if_sqlserver_disable_constraints_triggers(
    session: SqlASession, tablename: str
) -> None:
    """
    If we're running under SQL Server, disable triggers AND constraints for the
    specified table while the resource is held.

    Args:
        session: SQLAlchemy :class:`Session`
        tablename: table name
    """
    with if_sqlserver_disable_constraints(session, tablename):
        with if_sqlserver_disable_triggers(session, tablename):
            yield
