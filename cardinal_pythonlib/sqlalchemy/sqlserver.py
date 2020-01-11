#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/sqlserver.py

"""
===============================================================================

    Original code copyright (C) 2009-2020 Rudolf Cardinal (rudolf@pobox.com).

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

**SQLAlchemy functions specific to Microsoft SQL Server.**

"""

from contextlib import contextmanager

from sqlalchemy.orm import Session as SqlASession

from cardinal_pythonlib.sqlalchemy.dialect import quote_identifier
from cardinal_pythonlib.sqlalchemy.engine_func import is_sqlserver
from cardinal_pythonlib.sqlalchemy.session import get_engine_from_session


# =============================================================================
# Workarounds for SQL Server "DELETE takes forever" bug
# =============================================================================

@contextmanager
def if_sqlserver_disable_constraints(session: SqlASession,
                                     tablename: str) -> None:
    """
    If we're running under SQL Server, disable constraint checking for the
    specified table while the resource is held.

    Args:
        session: SQLAlchemy :class:`Session`
        tablename: table name

    See
    https://stackoverflow.com/questions/123558/sql-server-2005-t-sql-to-temporarily-disable-a-trigger
    """  # noqa
    engine = get_engine_from_session(session)
    if is_sqlserver(engine):
        quoted_tablename = quote_identifier(tablename, engine)
        session.execute(
            f"ALTER TABLE {quoted_tablename} NOCHECK CONSTRAINT all")
        yield
        session.execute(
            f"ALTER TABLE {quoted_tablename} WITH CHECK CHECK CONSTRAINT all")
    else:
        yield


@contextmanager
def if_sqlserver_disable_triggers(session: SqlASession,
                                  tablename: str) -> None:
    """
    If we're running under SQL Server, disable triggers for the specified table
    while the resource is held.

    Args:
        session: SQLAlchemy :class:`Session`
        tablename: table name

    See
    https://stackoverflow.com/questions/123558/sql-server-2005-t-sql-to-temporarily-disable-a-trigger
    """  # noqa
    engine = get_engine_from_session(session)
    if is_sqlserver(engine):
        quoted_tablename = quote_identifier(tablename, engine)
        session.execute(
            f"ALTER TABLE {quoted_tablename} DISABLE TRIGGER all")
        yield
        session.execute(
            f"ALTER TABLE {quoted_tablename} ENABLE TRIGGER all")
    else:
        yield


@contextmanager
def if_sqlserver_disable_constraints_triggers(session: SqlASession,
                                              tablename: str) -> None:
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
