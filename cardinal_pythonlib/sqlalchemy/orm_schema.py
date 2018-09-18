#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/schema.py

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

**Functions to work with SQLAlchemy schemas (schemata) via ORM objects.**

"""

import logging
from typing import TYPE_CHECKING

from cardinal_pythonlib.logs import BraceStyleAdapter
from cardinal_pythonlib.sqlalchemy.session import get_safe_url_from_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.schema import CreateTable

if TYPE_CHECKING:
    from sqlalchemy.sql.schema import Table

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# Create single table from SQLAlchemy ORM class
# =============================================================================

def create_table_from_orm_class(engine: Engine,
                                ormclass: DeclarativeMeta,
                                without_constraints: bool = False) -> None:
    """
    From an SQLAlchemy ORM class, creates the database table via the specified
    engine, using a ``CREATE TABLE`` SQL (DDL) statement.

    Args:
        engine: SQLAlchemy :class:`Engine` object
        ormclass: SQLAlchemy ORM class
        without_constraints: don't add foreign key constraints
    """
    table = ormclass.__table__  # type: Table
    log.info("Creating table {} on engine {}{}",
             table.name,
             get_safe_url_from_engine(engine),
             " (omitting constraints)" if without_constraints else "")
    # https://stackoverflow.com/questions/19175311/how-to-create-only-one-table-with-sqlalchemy  # noqa
    if without_constraints:
        include_foreign_key_constraints = []
    else:
        include_foreign_key_constraints = None  # the default
    creator = CreateTable(
        table,
        include_foreign_key_constraints=include_foreign_key_constraints
    )
    creator.execute(bind=engine)
