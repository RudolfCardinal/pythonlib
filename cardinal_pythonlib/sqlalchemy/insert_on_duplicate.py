#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/insert_on_duplicate.py

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

**Add "INSERT ON DUPLICATE KEY UPDATE" functionality to SQLAlchemy for MySQL.**

OLD VERSION (before SQLAlchemy 1.4/future=True or SQLAlchemy 2.0):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- https://www.reddit.com/r/Python/comments/p5grh/sqlalchemy_whats_the_idiomatic_way_of_writing/
- https://github.com/bedwards/sqlalchemy_mysql_ext/blob/master/duplicate.py
  ... modified
- https://docs.sqlalchemy.org/en/rel_1_0/core/compiler.html
- https://stackoverflow.com/questions/6611563/sqlalchemy-on-duplicate-key-update
- https://dev.mysql.com/doc/refman/5.7/en/insert-on-duplicate.html

Once implemented, you can do

.. code-block:: python

    q = sqla_table.insert_on_duplicate().values(destvalues)
    session.execute(q)

**Then: this partly superseded by SQLAlchemy v1.2:**

- https://docs.sqlalchemy.org/en/latest/changelog/migration_12.html
- https://docs.sqlalchemy.org/en/latest/dialects/mysql.html#mysql-insert-on-duplicate-key-update


FOR SQLAlchemy 1.4/future=True OR SQLAlchemy 2.0:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

New function: insert_with_upsert_if_supported().

"""  # noqa: E501

# =============================================================================
# Imports
# =============================================================================

import logging
from typing import Dict

from cardinal_pythonlib.sqlalchemy.dialect import get_dialect_name
from sqlalchemy.dialects.mysql import insert as insert_mysql
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.schema import Table
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import Insert

from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName

log = logging.getLogger(__name__)


# =============================================================================
# insert_with_upsert_if_supported
# =============================================================================


def insert_with_upsert_if_supported(
    table: Table,
    values: Dict,
    session: Session = None,
    dialect: Dialect = None,
) -> Insert:
    """
    Creates an "upsert" (INSERT ... ON DUPLICATE KEY UPDATE) statment if
    possible (e.g. MySQL/MariaDB). Failing that, returns an INSERT statement.

    Args:
        table:
            SQLAlchemy Table in which to insert values.
        values:
            Values to insert (column: value dictionary).
        session:
            Session from which to extract a dialect.
        dialect:
            Explicit dialect.

    Previously (prior to 2025-01-05 and prior to SQLAlchemy 2), we did this:

    .. code-block:: python

        q = sqla_table.insert_on_duplicate().values(destvalues)

    This "insert_on_duplicate" member was available because
    crate_anon/anonymise/config.py ran monkeypatch_TableClause(), from
    cardinal_pythonlib.sqlalchemy.insert_on_duplicate. The function did dialect
    detection via "@compiles(InsertOnDuplicate, SqlaDialectName.MYSQL)". But
    it did nasty text-based hacking to get the column names.

    However, SQLAlchemy now supports "upsert" for MySQL:
    https://docs.sqlalchemy.org/en/20/dialects/mysql.html#insert-on-duplicate-key-update-upsert

    Note the varying argument forms possible.

    The only other question: if the dialect is not MySQL, will the reference to
    insert_stmt.on_duplicate_key_update crash or just not do anything? To test:

    .. code-block:: python

        from sqlalchemy import table
        t = table("tablename")
        destvalues = {"a": 1}

        insert_stmt = t.insert().values(destvalues)
        on_dup_key_stmt = insert_stmt.on_duplicate_key_update(destvalues)

    This does indeed crash (AttributeError: 'Insert' object has no attribute
    'on_duplicate_key_update'). In contrast, this works:

    .. code-block:: python

        from sqlalchemy.dialects.mysql import insert as insert_mysql

        insert2 = insert_mysql(t).values(destvalues)
        on_dup_key2 = insert2.on_duplicate_key_update(destvalues)

    Note also that an insert() statement doesn't gain a
    "on_duplicate_key_update" attribute just because MySQL is used (the insert
    statement doesn't know that yet).

    The old way was good for dialect detection but ugly for textual analysis of
    the query. The new way is more elegant in the query, but less for dialect
    detection. Overall, new way likely preferable.

    """
    if bool(session) + bool(dialect) != 1:
        raise ValueError(
            f"Must specify exactly one of: {session=}, {dialect=}"
        )
    dialect_name = get_dialect_name(dialect or session)
    if dialect_name == SqlaDialectName.MYSQL:
        return (
            insert_mysql(table).values(values).on_duplicate_key_update(values)
        )
    else:
        return table.insert().values(values)
