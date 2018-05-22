#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/orm_query.py

"""
===============================================================================
    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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
from typing import Any, Dict, Sequence, Tuple, Union

from sqlalchemy.engine.base import Connection, Engine
from sqlalchemy.engine.result import ResultProxy
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import ClauseElement, literal
from sqlalchemy.sql import func
from sqlalchemy.sql.selectable import Exists

from cardinal_pythonlib.logs import BraceStyleAdapter
from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# Get query result with fieldnames
# =============================================================================

def get_rows_fieldnames_from_query(
        session: Union[Session, Engine, Connection],
        query: Query) -> Tuple[Sequence[Sequence[Any]], Sequence[str]]:
    # https://stackoverflow.com/questions/6455560/how-to-get-column-names-from-sqlalchemy-result-declarative-syntax  # noqa
    # No! Returns e.g. "User" for session.Query(User)...
    # fieldnames = [cd['name'] for cd in query.column_descriptions]
    result = session.execute(query)  # type: ResultProxy
    fieldnames = result.keys()
    # ... yes! Comes out as "_table_field", which is how SQLAlchemy SELECTs
    # things.
    rows = result.fetchall()
    return rows, fieldnames


# =============================================================================
# EXISTS (SQLAlchemy ORM)
# =============================================================================

def bool_from_exists_clause(session: Session,
                            exists_clause: Exists) -> bool:
    """
    Database dialects are not consistent in how EXISTS clauses can be converted
    to a boolean answer.

    See:
    - https://bitbucket.org/zzzeek/sqlalchemy/issues/3212/misleading-documentation-for-queryexists  # noqa
    - http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.exists  # noqa
    """
    if session.get_bind().dialect.name == SqlaDialectName.MSSQL:
        # SQL Server
        result = session.query(literal(True)).filter(exists_clause).scalar()
        # SELECT 1 WHERE EXISTS (SELECT 1 FROM table WHERE ...)
        # ... giving 1 or None (no rows)
        # ... fine for SQL Server, but invalid for MySQL (no FROM clause)
    else:
        # MySQL, etc.
        result = session.query(exists_clause).scalar()
        # SELECT EXISTS (SELECT 1 FROM table WHERE ...)
        # ... giving 1 or 0
        # ... fine for MySQL, but invalid syntax for SQL server
    return bool(result)


def exists_orm(session: Session,
               ormclass: DeclarativeMeta,
               *criteria: Any) -> bool:
    """
    Example usage:
        bool_exists = exists_orm(session, MyClass, MyClass.myfield == value)
    """
    # http://docs.sqlalchemy.org/en/latest/orm/query.html
    q = session.query(ormclass)
    for criterion in criteria:
        q = q.filter(criterion)
    exists_clause = q.exists()
    return bool_from_exists_clause(session=session,
                                   exists_clause=exists_clause)


# =============================================================================
# Get or create (SQLAlchemy ORM)
# =============================================================================
# http://stackoverflow.com/questions/2546207
# ... composite of several suggestions

def get_or_create(session: Session,
                  model: DeclarativeMeta,
                  defaults: Dict[str, Any] = None,
                  **kwargs: Any) -> Tuple[Any, bool]:
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = dict((k, v) for k, v in kwargs.items()
                      if not isinstance(v, ClauseElement))
        params.update(defaults or {})
        instance = model(**params)
        session.add(instance)
        return instance, True


# =============================================================================
# Extend Query to provide an optimized COUNT(*)
# =============================================================================

# noinspection PyAbstractClass
class CountStarSpecializedQuery(Query):
    """
    Optimizes COUNT(*) queries.
    See
        https://stackoverflow.com/questions/12941416/how-to-count-rows-with-select-count-with-sqlalchemy  # noqa

    Example use:
        q = CountStarSpecializedQuery([cls], session=dbsession)\
            .filter(cls.username == username)
        return q.count_star()
    """
    def count_star(self) -> int:
        count_query = (self.statement.with_only_columns([func.count()])
                       .order_by(None))
        return self.session.execute(count_query).scalar()
