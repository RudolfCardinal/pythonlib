#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/engine_func.py

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

**Functions to help with SQLAlchemy Engines.**

"""

from typing import Tuple, TYPE_CHECKING

from cardinal_pythonlib.sqlalchemy.dialect import (
    get_dialect_name,
    SqlaDialectName,
)

if TYPE_CHECKING:
    from sqlalchemy.engine.base import Engine
    from sqlalchemy.engine.result import ResultProxy


# =============================================================================
# Helper functions for SQL Server
# =============================================================================

def is_sqlserver(engine: "Engine") -> bool:
    """
    Is the SQLAlchemy :class:`Engine` a Microsoft  SQL Server database?
    """
    dialect_name = get_dialect_name(engine)
    return dialect_name == SqlaDialectName.SQLSERVER


def get_sqlserver_product_version(engine: "Engine") -> Tuple[int]:
    """
    Gets SQL Server version information.

    Attempted to use ``dialect.server_version_info``:

    .. code-block:: python

        from sqlalchemy import create_engine

        url = "mssql+pyodbc://USER:PASSWORD@ODBC_NAME"
        engine = create_engine(url)
        dialect = engine.dialect
        vi = dialect.server_version_info

    Unfortunately, ``vi == ()`` for an SQL Server 2014 instance via
    ``mssql+pyodbc``. It's also ``None`` for a ``mysql+pymysql`` connection. So
    this seems ``server_version_info`` is a badly supported feature.

    So the only other way is to ask the database directly. The problem is that
    this requires an :class:`Engine` or similar. (The initial hope was to be
    able to use this from within SQL compilation hooks, to vary the SQL based
    on the engine version. Still, this isn't so bad.)

    We could use either

    .. code-block:: sql

        SELECT @@version;  -- returns a human-readable string
        SELECT SERVERPROPERTY('ProductVersion');  -- better

    The ``pyodbc`` interface will fall over with ``ODBC SQL type -150 is not
    yet supported`` with that last call, though, meaning that a ``VARIANT`` is
    coming back, so we ``CAST`` as per the source below.
    """
    assert is_sqlserver(engine), (
        "Only call get_sqlserver_product_version() for Microsoft SQL Server "
        "instances."
    )
    sql = "SELECT CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR)"
    rp = engine.execute(sql)  # type: ResultProxy
    row = rp.fetchone()
    dotted_version = row[0]  # type: str  # e.g. '12.0.5203.0'
    return tuple(int(x) for x in dotted_version.split("."))


# https://www.mssqltips.com/sqlservertip/1140/how-to-tell-what-sql-server-version-you-are-running/  # noqa
SQLSERVER_MAJOR_VERSION_2000 = 8
SQLSERVER_MAJOR_VERSION_2005 = 9
SQLSERVER_MAJOR_VERSION_2008 = 10
SQLSERVER_MAJOR_VERSION_2012 = 11
SQLSERVER_MAJOR_VERSION_2014 = 12
SQLSERVER_MAJOR_VERSION_2016 = 13
SQLSERVER_MAJOR_VERSION_2017 = 14


def is_sqlserver_2008_or_later(engine: "Engine") -> bool:
    """
    Is the SQLAlchemy :class:`Engine` an instance of Microsoft SQL Server,
    version 2008 or later?
    """
    if not is_sqlserver(engine):
        return False
    version_tuple = get_sqlserver_product_version(engine)
    return version_tuple >= (SQLSERVER_MAJOR_VERSION_2008, )
