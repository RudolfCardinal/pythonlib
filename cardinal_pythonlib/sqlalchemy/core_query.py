#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/core_query.py

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

from typing import Any, Optional, Sequence, Tuple, Union

from sqlalchemy.engine.base import Connection, Engine
from sqlalchemy.engine.result import ResultProxy
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import (
    column, exists, func, literal, select, table,
)


# =============================================================================
# Get query result with fieldnames
# =============================================================================

def get_rows_fieldnames_from_raw_sql(
        session: Union[Session, Engine, Connection],
        sql: str) -> Tuple[Sequence[Sequence[Any]], Sequence[str]]:
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

def exists_plain(session: Session, tablename: str, *criteria: Any) -> bool:
    exists_clause = exists().select_from(table(tablename))
    # ... EXISTS (SELECT * FROM tablename)
    for criterion in criteria:
        exists_clause = exists_clause.where(criterion)
    # ... EXISTS (SELECT * FROM tablename WHERE ...)

    if session.get_bind().dialect.name == 'mssql':
        query = select([literal(True)]).where(exists_clause)
        # ... SELECT 1 WHERE EXISTS (SELECT * FROM tablename WHERE ...)
    else:
        query = select([exists_clause])
        # ... SELECT EXISTS (SELECT * FROM tablename WHERE ...)

    result = session.execute(query).scalar()
    return bool(result)
