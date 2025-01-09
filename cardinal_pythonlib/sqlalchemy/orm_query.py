#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/orm_query.py

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

**Functions to perform and manipulate SQLAlchemy ORM queries.**

"""

from typing import Any, Dict, List, Tuple, Type, Union

from sqlalchemy.engine.base import Connection, Engine
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import ClauseElement, literal, select
from sqlalchemy.sql import func
from sqlalchemy.sql.selectable import Exists

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler
from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Get query result with fieldnames
# =============================================================================


# noinspection PyUnusedLocal
def get_rows_fieldnames_from_query(
    session: Union[Session, Engine, Connection], query: Query
) -> Tuple[List[Tuple[Any, ...]], List[str]]:
    """
    Superseded. It used to be fine to use a Query object to run a SELECT
    statement. But as of SQLAlchemy 2.0 (or 1.4 with future=True), this has
    been removed.

    Also, it isn't worth coercing here. Some details are in the source code,
    but usually we are not seeking to run a query that fetches ORM objects
    themselves and then map those to fieldnames/values. Instead, we used to use
    a Query object made from selectable elements like columns and COUNT()
    clauses. That is what the select() system is meant for. So this code will
    now raise an error.
    """
    raise NotImplementedError(
        "From SQLAlchemy 2.0, don't perform queries directly with a "
        "sqlalchemy.orm.query.Query object; use a "
        "sqlalchemy.sql.selectable.Select object, e.g. from select(). Use "
        "cardinal_pythonlib.sqlalchemy.core_query."
        "get_rows_fieldnames_from_select() instead."
    )

    # - Old and newer advice:
    #   https://stackoverflow.com/questions/6455560/how-to-get-column-names-from-sqlalchemy-result-declarative-syntax  # noqa: E501
    #
    # 1. query.column_description
    #    fieldnames = [cd['name'] for cd in query.column_descriptions]
    #    No. Returns e.g. "User" for session.Query(User), i.e. ORM class names.
    # 2. Formerly (prior to SQLAlchemy 1.4+/future=True), result.keys() worked.
    #    It came out as "_table_field", which is how SQLAlchemy SELECTs things.
    # 3. But now, use query.statement.columns.keys().
    #    Or possible query.statement.subquery().columns.keys().
    #
    # In SQLAlchemy 2, the result of session.execute(query) is typically a
    # sqlalchemy.engine.result.ChunkedIteratorResult. Then, "result.mappings()"
    # gives a sqlalchemy.engine.result.MappingResult. See
    # https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.Result  # noqa: E501
    # In the context of the Core/declarative methods, results.mappings() is
    # useful and gives a dictionary. But when you do it here, you get a
    # dictionary of {classname: classinstance}, which is less helpful.

    # FIELDNAMES ARE ACHIEVABLE LIKE THIS:
    #
    # fieldnames = query.statement.subquery().columns.keys()
    #
    # Without "subquery()":
    # SADeprecationWarning: The SelectBase.c and SelectBase.columns attributes
    # are deprecated and will be removed in a future release; these attributes
    # implicitly create a subquery that should be explicit.  Please call
    # SelectBase.subquery() first in order to create a subquery, which then
    # contains this attribute.  To access the columns that this SELECT object
    # SELECTs from, use the SelectBase.selected_columns attribute. (deprecated
    # since: 1.4)

    # VALUES ARE ACHIEVABLE ALONG THESE LINES [although session.execute(query)
    # is no longer legitimate] BUT IT IS A BIT SILLY.
    #
    # https://docs.sqlalchemy.org/en/14/errors.html#error-89ve
    #
    # result = session.execute(query)
    # rows_as_object_tuples = result.fetchall()
    # orm_objects = tuple(row[0] for row in rows_as_object_tuples)
    # rows = [
    #         tuple(getattr(obj, k) for k in fieldnames)
    #     for obj in orm_objects
    # ]

    # return rows, fieldnames


# =============================================================================
# EXISTS (SQLAlchemy ORM)
# =============================================================================


def bool_from_exists_clause(session: Session, exists_clause: Exists) -> bool:
    """
    Database dialects are not consistent in how ``EXISTS`` clauses can be
    converted to a boolean answer. This function manages the inconsistencies.

    See:

    - https://bitbucket.org/zzzeek/sqlalchemy/issues/3212/misleading-documentation-for-queryexists
    - https://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.exists

    Specifically, we want this:

    *SQL Server*

    .. code-block:: sql

        SELECT 1 WHERE EXISTS (SELECT 1 FROM table WHERE ...)
        -- ... giving 1 or None (no rows)
        -- ... fine for SQL Server, but invalid for MySQL (no FROM clause)
        -- ... also fine for SQLite, giving 1 or None (no rows)

    *Others, including MySQL*

    .. code-block:: sql

        SELECT EXISTS (SELECT 1 FROM table WHERE ...)
        -- ... giving 1 or 0
        -- ... fine for MySQL, but invalid syntax for SQL Server
        -- ... also fine for SQLite, giving 1 or 0

    """  # noqa: E501
    if session.get_bind().dialect.name == SqlaDialectName.MSSQL:
        # SQL Server
        result = session.query(literal(True)).filter(exists_clause).scalar()
    else:
        # MySQL, etc.
        result = session.query(exists_clause).scalar()
    return bool(result)


def exists_orm(
    session: Session, ormclass: Type[DeclarativeMeta], *criteria: Any
) -> bool:
    """
    Detects whether a database record exists for the specified ``ormclass``
    and ``criteria``.

    Example usage:

    .. code-block:: python

        bool_exists = exists_orm(session, MyClass, MyClass.myfield == value)
    """
    # http://docs.sqlalchemy.org/en/latest/orm/query.html
    q = session.query(ormclass)
    for criterion in criteria:
        q = q.filter(criterion)
    exists_clause = q.exists()
    return bool_from_exists_clause(
        session=session, exists_clause=exists_clause
    )


# =============================================================================
# Get or create (SQLAlchemy ORM)
# =============================================================================


def get_or_create(
    session: Session,
    model: Type[DeclarativeMeta],
    defaults: Dict[str, Any] = None,
    **kwargs: Any
) -> Tuple[Any, bool]:
    """
    Fetches an ORM object from the database, or creates one if none existed.

    Args:
        session: an SQLAlchemy :class:`Session`
        model: an SQLAlchemy ORM class
        defaults: default initialization arguments (in addition to relevant
            filter criteria) if we have to create a new instance
        kwargs: optional filter criteria

    Returns:
        a tuple ``(instance, newly_created)``

    See https://stackoverflow.com/questions/2546207 (this function is a
    composite of several suggestions).
    """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = dict(
            (k, v)
            for k, v in kwargs.items()
            if not isinstance(v, ClauseElement)
        )
        params.update(defaults or {})
        instance = model(**params)
        session.add(instance)
        return instance, True


# =============================================================================
# Extend Query to provide an optimized COUNT(*)
# =============================================================================


# noinspection PyAbstractClass
class CountStarSpecializedQuery:
    def __init__(self, model: Type[DeclarativeMeta], session: Session) -> None:
        """
        Optimizes ``COUNT(*)`` queries.

        Given an ORM class, and a session, creates a query that counts
        instances of that ORM class. (You can filter later using the filter()
        command, which chains as usual.)

        See
        https://stackoverflow.com/questions/12941416/how-to-count-rows-with-select-count-with-sqlalchemy

        Example use:

        .. code-block:: python

            q = CountStarSpecializedQuery(cls, session=dbsession)\
                .filter(cls.username == username)
            return q.count_star()

        Note that in SQLAlchemy <1.4, Query(ormclass) implicitly added "from
        the table of that ORM class". But SQLAlchemy 2.0 doesn't. That means
        that Query(ormclass) leads ultimately to "SELECT COUNT(*)" by itself;
        somewhat surprisingly to me, that gives 1 rather than an error, at
        least in SQLite. So now we inherit from Select, not Query.

        """
        # https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.select  # noqa: E501
        # ... accepts "series of ColumnElement and / or FromClause objects"
        # But passing the table to select() just means you select too many
        # columns. So let's do this by embedding, not inheriting from, a
        # select()-type object (Select).
        self.select_query = select(func.count()).select_from(model.__table__)
        self.session = session

    def filter(self, *args, **kwargs) -> "CountStarSpecializedQuery":
        self.select_query = self.select_query.filter(*args, **kwargs)
        return self

    def count_star(self) -> int:
        """
        Implements the ``COUNT(*)`` specialization.
        """
        count_query = self.select_query.order_by(None)
        return self.session.execute(count_query).scalar()
