#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/core_query.py

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

**Query helper functions using the SQLAlchemy Core.**

"""

import logging
from typing import Any, List, Optional, Sequence, Tuple, Union

from sqlalchemy.engine.base import Connection, Engine
from sqlalchemy.engine.result import ResultProxy
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import (
    column, exists, func, literal, select, table,
)
from sqlalchemy.sql.schema import Table
from sqlalchemy.sql.selectable import Select

from cardinal_pythonlib.logs import BraceStyleAdapter
from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# Get query result with fieldnames
# =============================================================================

def get_rows_fieldnames_from_raw_sql(
        session: Union[Session, Engine, Connection],
        sql: str) -> Tuple[Sequence[Sequence[Any]], Sequence[str]]:
    """
    Returns results and column names from a query.

    Args:
        session: SQLAlchemy :class:`Session`, :class:`Engine`, or
            :class:`Connection` object
        sql: raw SQL to execure

    Returns:
        ``(rows, fieldnames)`` where ``rows`` is the usual set of results and
        ``fieldnames`` are the name of the result columns/fields.

    """
    result = session.execute(sql)  # type: ResultProxy
    fieldnames = result.keys()
    rows = result.fetchall()
    return rows, fieldnames


# =============================================================================
# SELECT COUNT(*) (SQLAlchemy Core)
# =============================================================================
# http://stackoverflow.com/questions/12941416

def count_star(session: Union[Session, Engine, Connection],
               tablename: str,
               *criteria: Any) -> int:
    """
    Returns the result of ``COUNT(*)`` from the specified table (with
    additional ``WHERE`` criteria if desired).

    Args:
        session: SQLAlchemy :class:`Session`, :class:`Engine`, or
            :class:`Connection` object
        tablename: name of the table
        criteria: optional SQLAlchemy "where" criteria

    Returns:
        a scalar
    """
    # works if you pass a connection or a session or an engine; all have
    # the execute() method
    query = select([func.count()]).select_from(table(tablename))
    for criterion in criteria:
        query = query.where(criterion)
    return session.execute(query).scalar()


# =============================================================================
# SELECT COUNT(*), MAX(field) (SQLAlchemy Core)
# =============================================================================

def count_star_and_max(session: Union[Session, Engine, Connection],
                       tablename: str,
                       maxfield: str,
                       *criteria: Any) -> Tuple[int, Optional[int]]:
    """

    Args:
        session: SQLAlchemy :class:`Session`, :class:`Engine`, or
            :class:`Connection` object
        tablename: name of the table
        maxfield: name of column (field) to take the ``MAX()`` of
        criteria: optional SQLAlchemy "where" criteria

    Returns:
        a tuple: ``(count, maximum)``

    """
    query = select([
        func.count(),
        func.max(column(maxfield))
    ]).select_from(table(tablename))
    for criterion in criteria:
        query = query.where(criterion)
    result = session.execute(query)
    return result.fetchone()  # count, maximum


# =============================================================================
# SELECT EXISTS (SQLAlchemy Core)
# =============================================================================
# http://stackoverflow.com/questions/15381604
# http://docs.sqlalchemy.org/en/latest/orm/query.html

def exists_in_table(session: Session, table_: Table, *criteria: Any) -> bool:
    """
    Implements an efficient way of detecting if a record or records exist;
    should be faster than ``COUNT(*)`` in some circumstances.

    Args:
        session: SQLAlchemy :class:`Session`, :class:`Engine`, or
            :class:`Connection` object
        table_: SQLAlchemy :class:`Table` object
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

    if session.get_bind().dialect.name == SqlaDialectName.MSSQL:
        query = select([literal(True)]).where(exists_clause)
        # ... SELECT 1 WHERE EXISTS (SELECT * FROM tablename WHERE ...)
    else:
        query = select([exists_clause])
        # ... SELECT EXISTS (SELECT * FROM tablename WHERE ...)

    result = session.execute(query).scalar()
    return bool(result)


def exists_plain(session: Session, tablename: str, *criteria: Any) -> bool:
    """
    Implements an efficient way of detecting if a record or records exist;
    should be faster than COUNT(*) in some circumstances.

    Args:
        session: SQLAlchemy :class:`Session`, :class:`Engine`, or
            :class:`Connection` object
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

def fetch_all_first_values(session: Session,
                           select_statement: Select) -> List[Any]:
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
    rows = session.execute(select_statement)  # type: ResultProxy
    try:
        return [x for (x,) in rows]
    except ValueError as e:
        raise MultipleResultsFound(str(e))
