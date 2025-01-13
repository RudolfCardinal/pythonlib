#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/core_query.py

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

**Query helper functions using the SQLAlchemy Core.**

"""

from typing import Any, List, Optional, Tuple, Union

from sqlalchemy.engine.base import Connection, Engine
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import (
    case,
    column,
    exists,
    func,
    select,
    table,
    text,
)
from sqlalchemy.sql.schema import Table
from sqlalchemy.sql.selectable import Select, TableClause

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Get query result with fieldnames
# =============================================================================


def get_rows_fieldnames_from_raw_sql(
    session: Union[Session, Engine, Connection], sql: str
) -> Tuple[List[Row], List[str]]:
    """
    Returns results and column names from a query.

    Args:
        session:
            SQLAlchemy :class:`Session`, :class:`Engine` (SQL Alchemy 1.4
            only), or :class:`Connection` object
        sql:
            raw SQL to execure

    Returns:
        ``(rows, fieldnames)`` where ``rows`` is the usual set of results and
        ``fieldnames`` are the name of the result columns/fields.

    """
    if not isinstance(sql, str):
        raise ValueError("sql argument must be a string")
    result = session.execute(text(sql))
    fieldnames = result.keys()
    rows = result.fetchall()
    return rows, fieldnames


def get_rows_fieldnames_from_select(
    session: Union[Session, Engine, Connection], select_query: Select
) -> Tuple[List[Row], List[str]]:
    """
    Returns results and column names from a query.

    Args:
        session:
            SQLAlchemy :class:`Session`, :class:`Engine` (SQL Alchemy 1.4
            only), or :class:`Connection` object
        select_query:
            select() statement, i.e. instance of
            :class:`sqlalchemy.sql.selectable.Select`

    Returns:
        ``(rows, fieldnames)`` where ``rows`` is the usual set of results and
        ``fieldnames`` are the name of the result columns/fields.

    """
    if not isinstance(select_query, Select):
        raise ValueError("select_query argument must be a select() statement")

    # Check that the user is not querying an ORM *class* rather than columns.
    # It doesn't make much sense to use this function in that case.
    # If Pet is an ORM class (see unit tests!), then:
    #
    # - select(Pet).column_descriptions:
    #
    #   [{'name': 'Pet', 'type': <class 'orm_query_tests.Pet'>, 'aliased':
    #   False, 'expr': <class 'orm_query_tests.Pet'>, 'entity': <class
    #   'orm_query_tests.Pet'>}]
    #
    #   "entity" matches "type"; this is the one we want to disallow
    #
    # - select(Pet.id, Pet.name).column_descriptions:
    #
    #   [{'name': 'id', 'type': Integer(), 'aliased': False, 'expr':
    #   <sqlalchemy.orm.attributes.InstrumentedAttribute object at
    #   0x7bda9e1b7330>, 'entity': <class 'orm_query_tests.Pet'>}, {'name':
    #   'name', 'type': String(length=50), 'aliased': False, 'expr':
    #   <sqlalchemy.orm.attributes.InstrumentedAttribute object at
    #   0x7bda9e1b7380>, 'entity': <class 'orm_query_tests.Pet'>}]
    #
    #  ... "entity" differs from "type"
    #
    # - select(sometable.a, sometable.b).column_descriptions:
    #
    #   [{'name': 'a', 'type': INTEGER(), 'expr': Column('a', INTEGER(),
    #   table=<t>, primary_key=True)}, {'name': 'b', 'type': INTEGER(), 'expr':
    #   Column('b', INTEGER(), table=<t>)}]
    #
    #   ... no "entity" key.
    #
    # Therefore:
    for cd in select_query.column_descriptions:
        # https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.Select.column_descriptions  # noqa: E501
        # For
        if "entity" not in cd:
            continue
        if cd["type"] == cd["entity"]:
            raise ValueError(
                "It looks like your select() query is querying whole ORM "
                "object classes, not just columns or column-like "
                "expressions. Its column_descriptions are: "
                f"{select_query.column_descriptions}"
            )

    result = session.execute(select_query)

    fieldnames_rmkview = result.keys()
    # ... of type RMKeyView, e.g. RMKeyView(['a', 'b'])
    fieldnames = [x for x in fieldnames_rmkview]

    rows = result.fetchall()

    # I don't know how to differentiate select(Pet), selecting an ORM class,
    # from select(Pet.name), selecting a column.

    return rows, fieldnames


# =============================================================================
# SELECT COUNT(*) (SQLAlchemy Core)
# =============================================================================
# https://stackoverflow.com/questions/12941416


def count_star(
    session: Union[Session, Engine, Connection], tablename: str, *criteria: Any
) -> int:
    """
    Returns the result of ``COUNT(*)`` from the specified table (with
    additional ``WHERE`` criteria if desired).

    Args:
        session:
            SQLAlchemy :class:`Session`, :class:`Engine` (SQL Alchemy 1.4
            only), or :class:`Connection` object
        tablename: name of the table
        criteria: optional SQLAlchemy "where" criteria

    Returns:
        a scalar
    """
    # works if you pass a connection or a session or an engine; all have
    # the execute() method
    query = select(func.count()).select_from(table(tablename))
    for criterion in criteria:
        query = query.where(criterion)
    return session.execute(query).scalar()


# =============================================================================
# SELECT COUNT(*), MAX(field) (SQLAlchemy Core)
# =============================================================================


def count_star_and_max(
    session: Union[Session, Engine, Connection],
    tablename: str,
    maxfield: str,
    *criteria: Any,
) -> Tuple[int, Optional[int]]:
    """

    Args:
        session:
            SQLAlchemy :class:`Session`, :class:`Engine` (SQL Alchemy 1.4
            only), or :class:`Connection` object
        tablename: name of the table
        maxfield: name of column (field) to take the ``MAX()`` of
        criteria: optional SQLAlchemy "where" criteria

    Returns:
        a tuple: ``(count, maximum)``

    """
    query = select(func.count(), func.max(column(maxfield))).select_from(
        table(tablename)
    )
    for criterion in criteria:
        query = query.where(criterion)
    result = session.execute(query)
    count, maximum = result.fetchone()
    return count, maximum


# =============================================================================
# SELECT EXISTS (SQLAlchemy Core)
# =============================================================================
# https://stackoverflow.com/questions/15381604
# http://docs.sqlalchemy.org/en/latest/orm/query.html


def exists_in_table(
    session: Session, table_: Union[Table, TableClause], *criteria: Any
) -> bool:
    """
    Implements an efficient way of detecting if a record or records exist;
    should be faster than ``COUNT(*)`` in some circumstances.

    Args:
        session:
            SQLAlchemy :class:`Session`, :class:`Engine` (SQL Alchemy 1.4
            only), or :class:`Connection` object
        table_: SQLAlchemy :class:`Table` object or table clause
        criteria: optional SQLAlchemy "where" criteria

    Returns:
        a boolean

    Prototypical use:

    .. code-block:: python

        return exists_in_table(session,
                               table,
                               column(fieldname1) == value2,
                               column(fieldname2) == value2)
    """
    exists_clause = exists().select_from(table_)
    # ... EXISTS (SELECT * FROM tablename)
    for criterion in criteria:
        exists_clause = exists_clause.where(criterion)
    # ... EXISTS (SELECT * FROM tablename WHERE ...)

    # Methods as follows.
    # SQL validation: http://developer.mimer.com/validator/
    # Standard syntax: https://en.wikipedia.org/wiki/SQL_syntax
    # We can make it conditional on dialect via
    #       session.get_bind().dialect.name
    # but it would be better not to need to.
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # SELECT 1 FROM mytable WHERE EXISTS (SELECT * FROM mytable WHERE ...)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # - Produces multiple results (a 1 for each row).
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # SELECT 1 WHERE EXISTS (SELECT * FROM tablename WHERE ...)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # - Produces either 1 or NULL (no rows).
    # - Implementation:
    #
    #       query = select(literal(True)).where(exists_clause)
    #       result = session.execute(query).scalar()
    #       return bool(result)  # None/0 become False; 1 becomes True
    #
    # - However, may be non-standard: no FROM clause.
    # - Works on SQL Server (empirically).
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # SELECT EXISTS (SELECT * FROM tablename WHERE ...)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # - Produces 0 or 1.
    # - Implementation:
    #
    #       query = select(exists_clause)
    #       result = session.execute(query).scalar()
    #       return bool(result)
    #
    # - But it may not be standard.
    #
    # - Supported by MySQL:
    #   - https://dev.mysql.com/doc/refman/8.4/en/exists-and-not-exists-subqueries.html  # noqa: E501
    #   - and an empirical test
    #
    #   Suported by SQLite:
    #   - https://www.sqlite.org/lang_expr.html#the_exists_operator
    #   - and an empirical test
    #
    #   Possibly not SQL Server.
    #
    #   Possibly not Databricks.
    #   - https://docs.databricks.com/en/sql/language-manual/sql-ref-syntax-qry-select.html  # noqa: E501
    #   - https://docs.databricks.com/en/sql/language-manual/sql-ref-syntax-qry-select-where.html  # noqa: E501
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # SELECT CASE WHEN EXISTS(SELECT * FROM tablename WHERE...) THEN 0 ELSE 1 END  # noqa: E501
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # - ANSI standard.
    #   - https://stackoverflow.com/questions/17284688/how-to-efficiently-check-if-a-table-is-empty  # noqa: E501
    # - Returns 0 or 1.
    # - May be possible to use "SELECT 1 FROM tablename" also, but unclear
    #   what's faster, and likely EXISTS() should optimise.
    # - Implementation as below.

    query = select(case((exists_clause, 1), else_=0))
    result = session.execute(query).scalar()
    return bool(result)  # None/0 become False; 1 becomes True


def exists_plain(session: Session, tablename: str, *criteria: Any) -> bool:
    """
    Implements an efficient way of detecting if a record or records exist;
    should be faster than COUNT(*) in some circumstances.

    Args:
        session:
            SQLAlchemy :class:`Session`, :class:`Engine` (SQL Alchemy 1.4
            only), or :class:`Connection` object
        tablename: name of the table
        criteria: optional SQLAlchemy "where" criteria

    Returns:
        a boolean

    Prototypical use:

    .. code-block:: python

        return exists_plain(config.destdb.session,
                            dest_table_name,
                            column(fieldname1) == value2,
                            column(fieldname2) == value2)
    """
    return exists_in_table(session, table(tablename), *criteria)


# =============================================================================
# Get all first values
# =============================================================================


def fetch_all_first_values(
    session: Session, select_statement: Select
) -> List[Any]:
    # noinspection HttpUrlsUsage
    """
    Returns a list of the first values in each row returned by a ``SELECT``
    query.

    A Core version of this sort of thing:
    http://xion.io/post/code/sqlalchemy-query-values.html

    Args:
        session: SQLAlchemy :class:`Session` object
        select_statement: SQLAlchemy :class:`Select` object

    Returns:
        a list of the first value of each result row

    """
    rows = session.execute(select_statement)
    try:
        return [row[0] for row in rows]
    except ValueError as e:
        raise MultipleResultsFound(str(e))
