#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/tests/insert_on_duplicate_tests.py

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

**Unit tests.**

"""

# =============================================================================
# Imports
# =============================================================================

import logging
from unittest import TestCase

from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.dialects.mysql.base import MySQLDialect
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm.session import Session
from sqlalchemy.exc import IntegrityError

from cardinal_pythonlib.sqlalchemy.insert_on_duplicate import (
    insert_with_upsert_if_supported,
)

log = logging.getLogger(__name__)


# =============================================================================
# Unit tests
# =============================================================================


class InsertOnDuplicateKeyUpdateTests(TestCase):
    def test_insert_with_upsert_if_supported_syntax(self) -> None:
        # noinspection PyPep8Naming
        Base = declarative_base()

        class OrmObject(Base):
            __tablename__ = "sometable"
            id = Column(Integer, primary_key=True)
            name = Column(String)

        sqlite_engine = create_engine("sqlite://", echo=True, future=True)
        Base.metadata.create_all(sqlite_engine)

        session = Session(sqlite_engine)

        d1 = dict(id=1, name="One")
        d2 = dict(id=2, name="Two")

        table = OrmObject.__table__

        insert_1 = table.insert().values(d1)
        insert_2 = table.insert().values(d2)
        session.execute(insert_1)
        session.execute(insert_2)
        with self.assertRaises(IntegrityError):
            session.execute(insert_1)

        upsert_1 = insert_with_upsert_if_supported(
            table=table, values=d1, session=session
        )
        odku = "ON DUPLICATE KEY UPDATE"
        self.assertFalse(odku in str(upsert_1))

        upsert_2 = insert_with_upsert_if_supported(
            table=table, values=d1, dialect=MySQLDialect()
        )
        self.assertTrue(odku in str(upsert_2))

        # We can't test fully here without a MySQL connection.
        # But syntax tested separately in upsert_test_1.sql
