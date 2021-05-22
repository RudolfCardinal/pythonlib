#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/sqlfunc.py

"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

**Functions to operate on SQL clauses for SQLAlchemy Core.**

"""

from typing import NoReturn, TYPE_CHECKING

from sqlalchemy.ext.compiler import compiles
# noinspection PyProtectedMember
from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.sql.sqltypes import Numeric

from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName
from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ClauseElement, ClauseList
    from sqlalchemy.sql.compiler import SQLCompiler

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Support functions
# =============================================================================

def fail_unknown_dialect(compiler: "SQLCompiler", task: str) -> NoReturn:
    """
    Raise :exc:`NotImplementedError` in relation to a dialect for which a
    function hasn't been implemented (with a helpful error message).
    """
    raise NotImplementedError(
        f"Don't know how to {task} on dialect {compiler.dialect!r}. "
        f"(Check also: if you printed the SQL before it was bound to an "
        f"engine, you will be trying to use a dialect like StrSQLCompiler, "
        f"which could be a reason for failure.)"
    )


def fetch_processed_single_clause(element: "ClauseElement",
                                  compiler: "SQLCompiler") -> str:
    """
    Takes a clause element that must have a single clause, and converts it
    to raw SQL text.
    """
    if len(element.clauses) != 1:
        raise TypeError(f"Only one argument supported; "
                        f"{len(element.clauses)} were passed")
    clauselist = element.clauses  # type: ClauseList
    first = clauselist.get_children()[0]
    return compiler.process(first)


# =============================================================================
# Extract year from a DATE/DATETIME etc.
# =============================================================================

# noinspection PyPep8Naming
class extract_year(FunctionElement):
    """
    Implements an SQLAlchemy :func:`extract_year` function, to extract the
    year from a date/datetime column.

    ``YEAR``, or ``func.year()``, is specific to some DBs, e.g. MySQL.
    So is ``EXTRACT``, or ``func.extract()``;
    https://modern-sql.com/feature/extract.

    This function therefore implements an ``extract_year`` function across
    multiple databases.

    Use this as:

    .. code-block:: python

      from cardinal_pythonlib.sqlalchemy.sqlfunc import extract_year

    ... then use :func:`extract_year` in an SQLAlchemy ``SELECT`` expression.

    Here's an example from CamCOPS:

    .. code-block:: python

        select_fields = [
            literal(cls.__tablename__).label("task"),
            extract_year(cls._when_added_batch_utc).label("year"),
            extract_month(cls._when_added_batch_utc).label("month"),
            func.count().label("num_tasks_added"),
        ]

    """
    type = Numeric()
    name = 'extract_year'


# noinspection PyUnusedLocal
@compiles(extract_year)
def extract_year_default(element: "ClauseElement",
                         compiler: "SQLCompiler", **kw) -> NoReturn:
    """
    Default implementation of :func:, which raises :exc:`NotImplementedError`.
    """
    fail_unknown_dialect(compiler, "extract year from date")


# noinspection PyUnusedLocal
@compiles(extract_year, SqlaDialectName.SQLSERVER)
@compiles(extract_year, SqlaDialectName.MYSQL)
def extract_year_year(element: "ClauseElement",
                      compiler: "SQLCompiler", **kw) -> str:
    # https://dev.mysql.com/doc/refman/5.5/en/date-and-time-functions.html#function_year  # noqa
    # https://docs.microsoft.com/en-us/sql/t-sql/functions/year-transact-sql
    clause = fetch_processed_single_clause(element, compiler)
    return f"YEAR({clause})"


# noinspection PyUnusedLocal
@compiles(extract_year, SqlaDialectName.ORACLE)
@compiles(extract_year, SqlaDialectName.POSTGRES)
def extract_year_extract(element: "ClauseElement",
                         compiler: "SQLCompiler", **kw) -> str:
    # https://docs.oracle.com/cd/B19306_01/server.102/b14200/functions050.htm
    clause = fetch_processed_single_clause(element, compiler)
    return f"EXTRACT(YEAR FROM {clause})"


# noinspection PyUnusedLocal
@compiles(extract_year, SqlaDialectName.SQLITE)
def extract_year_strftime(element: "ClauseElement",
                          compiler: "SQLCompiler", **kw) -> str:
    # https://sqlite.org/lang_datefunc.html
    clause = fetch_processed_single_clause(element, compiler)
    return f"STRFTIME('%Y', {clause})"


# =============================================================================
# Extract month from a DATE/DATETIME etc.
# =============================================================================

# noinspection PyPep8Naming
class extract_month(FunctionElement):
    """
    Implements an SQLAlchemy :func:`extract_month` function. See
    :func:`extract_year`.
    """
    type = Numeric()
    name = 'extract_month'


# noinspection PyUnusedLocal
@compiles(extract_month)
def extract_month_default(element: "ClauseElement",
                          compiler: "SQLCompiler", **kw) -> NoReturn:
    fail_unknown_dialect(compiler, "extract month from date")


# noinspection PyUnusedLocal
@compiles(extract_month, SqlaDialectName.SQLSERVER)
@compiles(extract_month, SqlaDialectName.MYSQL)
def extract_month_month(element: "ClauseElement",
                        compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return f"MONTH({clause})"


# noinspection PyUnusedLocal
@compiles(extract_month, SqlaDialectName.ORACLE)
@compiles(extract_year, SqlaDialectName.POSTGRES)
def extract_month_extract(element: "ClauseElement",
                          compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return f"EXTRACT(MONTH FROM {clause})"


# noinspection PyUnusedLocal
@compiles(extract_month, SqlaDialectName.SQLITE)
def extract_month_strftime(element: "ClauseElement",
                           compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return f"STRFTIME('%m', {clause})"


# =============================================================================
# Extract day (day of month, not day of week) from a DATE/DATETIME etc.
# =============================================================================

# noinspection PyPep8Naming
class extract_day_of_month(FunctionElement):
    """
    Implements an SQLAlchemy :func:`extract_day` function (to extract the day
    of the month from a date/datetime expression). See :func:`extract_year`.
    """
    type = Numeric()
    name = 'extract_day'


# noinspection PyUnusedLocal
@compiles(extract_day_of_month)
def extract_day_of_month_default(element: "ClauseElement",
                                 compiler: "SQLCompiler", **kw) -> NoReturn:
    fail_unknown_dialect(compiler, "extract day-of-month from date")


# noinspection PyUnusedLocal
@compiles(extract_day_of_month, SqlaDialectName.SQLSERVER)
@compiles(extract_day_of_month, SqlaDialectName.MYSQL)
def extract_day_of_month_day(element: "ClauseElement",
                             compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return f"DAY({clause})"


# noinspection PyUnusedLocal
@compiles(extract_day_of_month, SqlaDialectName.ORACLE)
@compiles(extract_year, SqlaDialectName.POSTGRES)
def extract_day_of_month_extract(element: "ClauseElement",
                                 compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return f"EXTRACT(DAY FROM {clause})"


# noinspection PyUnusedLocal
@compiles(extract_day_of_month, SqlaDialectName.SQLITE)
def extract_day_of_month_strftime(element: "ClauseElement",
                                  compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return f"STRFTIME('%d', {clause})"
