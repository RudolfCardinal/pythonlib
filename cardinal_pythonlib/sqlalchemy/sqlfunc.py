#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/sqlfunc.py

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

import logging
from typing import TYPE_CHECKING

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.sql.sqltypes import Numeric

from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName
from cardinal_pythonlib.logs import BraceStyleAdapter

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ClauseElement, ClauseList
    from sqlalchemy.sql.compiler import SQLCompiler

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# Support functions
# =============================================================================

def fail_unknown_dialect(compiler: "SQLCompiler", task: str) -> None:
    raise NotImplementedError(
        "Don't know how to {task} on dialect {dialect!r}. "
        "(Check also: if you printed the SQL before it was bound to an "
        "engine, you will be trying to use a dialect like StrSQLCompiler, "
        "which could be a reason for failure.)".format(
            task=task,
            dialect=compiler.dialect
        )
    )


def fetch_processed_single_clause(element: "ClauseElement",
                                  compiler: "SQLCompiler") -> str:
    if len(element.clauses) != 1:
        raise TypeError("Only one argument supported; {} were passed".format(
            len(element.clauses)))
    clauselist = element.clauses  # type: ClauseList
    first = clauselist.get_children()[0]
    return compiler.process(first)


# =============================================================================
# Extract year from a DATE/DATETIME etc.
# =============================================================================
# YEAR, or func.year(), is specific to some DBs, e.g. MySQL
# so is EXTRACT, or func.extract(); http://modern-sql.com/feature/extract
#
# Use this as:
#   from cardinal_pythonlib.sqlalchemy.sqlfunc import extract_year
# ... then use extract_year() in an SQLAlchemy SELECT expression.

# noinspection PyPep8Naming
class extract_year(FunctionElement):
    type = Numeric()
    name = 'extract_year'


# noinspection PyUnusedLocal
@compiles(extract_year)
def extract_year_default(element: "ClauseElement",
                         compiler: "SQLCompiler", **kw) -> None:
    fail_unknown_dialect(compiler, "extract year from date")


# noinspection PyUnusedLocal
@compiles(extract_year, SqlaDialectName.SQLSERVER)
@compiles(extract_year, SqlaDialectName.MYSQL)
def extract_year_year(element: "ClauseElement",
                      compiler: "SQLCompiler", **kw) -> str:
    # https://dev.mysql.com/doc/refman/5.5/en/date-and-time-functions.html#function_year  # noqa
    # https://docs.microsoft.com/en-us/sql/t-sql/functions/year-transact-sql
    clause = fetch_processed_single_clause(element, compiler)
    return "YEAR({})".format(clause)


# noinspection PyUnusedLocal
@compiles(extract_year, SqlaDialectName.ORACLE)
@compiles(extract_year, SqlaDialectName.POSTGRES)
def extract_year_extract(element: "ClauseElement",
                         compiler: "SQLCompiler", **kw) -> str:
    # https://docs.oracle.com/cd/B19306_01/server.102/b14200/functions050.htm
    clause = fetch_processed_single_clause(element, compiler)
    return "EXTRACT(YEAR FROM {})".format(clause)


# noinspection PyUnusedLocal
@compiles(extract_year, SqlaDialectName.SQLITE)
def extract_year_strftime(element: "ClauseElement",
                          compiler: "SQLCompiler", **kw) -> str:
    # https://sqlite.org/lang_datefunc.html
    clause = fetch_processed_single_clause(element, compiler)
    return "STRFTIME('%Y', {})".format(clause)


# =============================================================================
# Extract month from a DATE/DATETIME etc.
# =============================================================================

# noinspection PyPep8Naming
class extract_month(FunctionElement):
    type = Numeric()
    name = 'extract_month'


# noinspection PyUnusedLocal
@compiles(extract_month)
def extract_month_default(element: "ClauseElement",
                          compiler: "SQLCompiler", **kw) -> None:
    fail_unknown_dialect(compiler, "extract month from date")


# noinspection PyUnusedLocal
@compiles(extract_month, SqlaDialectName.SQLSERVER)
@compiles(extract_month, SqlaDialectName.MYSQL)
def extract_month_month(element: "ClauseElement",
                        compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return "MONTH({})".format(clause)


# noinspection PyUnusedLocal
@compiles(extract_month, SqlaDialectName.ORACLE)
@compiles(extract_year, SqlaDialectName.POSTGRES)
def extract_month_extract(element: "ClauseElement",
                          compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return "EXTRACT(MONTH FROM {})".format(clause)


# noinspection PyUnusedLocal
@compiles(extract_month, SqlaDialectName.SQLITE)
def extract_month_strftime(element: "ClauseElement",
                           compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return "STRFTIME('%m', {})".format(clause)


# =============================================================================
# Extract day (day of month, not day of week) from a DATE/DATETIME etc.
# =============================================================================

# noinspection PyPep8Naming
class extract_day_of_month(FunctionElement):
    type = Numeric()
    name = 'extract_day'


# noinspection PyUnusedLocal
@compiles(extract_day_of_month)
def extract_day_of_month_default(element: "ClauseElement",
                                 compiler: "SQLCompiler", **kw) -> None:
    fail_unknown_dialect(compiler, "extract day-of-month from date")


# noinspection PyUnusedLocal
@compiles(extract_day_of_month, SqlaDialectName.SQLSERVER)
@compiles(extract_day_of_month, SqlaDialectName.MYSQL)
def extract_day_of_month_day(element: "ClauseElement",
                             compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return "DAY({})".format(clause)


# noinspection PyUnusedLocal
@compiles(extract_day_of_month, SqlaDialectName.ORACLE)
@compiles(extract_year, SqlaDialectName.POSTGRES)
def extract_day_of_month_extract(element: "ClauseElement",
                                 compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return "EXTRACT(DAY FROM {})".format(clause)


# noinspection PyUnusedLocal
@compiles(extract_day_of_month, SqlaDialectName.SQLITE)
def extract_day_of_month_strftime(element: "ClauseElement",
                                  compiler: "SQLCompiler", **kw) -> str:
    clause = fetch_processed_single_clause(element, compiler)
    return "STRFTIME('%d', {})".format(clause)
