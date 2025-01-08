#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/tests/core_query_tests.py

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

from unittest import TestCase

from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker, Session
from sqlalchemy.sql.expression import column, select, table, text
from sqlalchemy.sql.schema import MetaData

from cardinal_pythonlib.sqlalchemy.core_query import (
    count_star_and_max,
    exists_in_table,
    exists_plain,
    fetch_all_first_values,
    get_rows_fieldnames_from_raw_sql,
    get_rows_fieldnames_from_select,
)
from cardinal_pythonlib.sqlalchemy.session import SQLITE_MEMORY_URL


# =============================================================================
# Unit tests
# =============================================================================


class CoreQueryTests(TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(SQLITE_MEMORY_URL, future=True)
        self.tablename = "t"
        self.a = "a"
        self.b = "b"
        self.a_val1 = 1
        self.a_val2 = 2
        self.b_val1 = 101
        self.b_val2 = 102
        with self.engine.begin() as con:
            con.execute(
                text(
                    f"CREATE TABLE {self.tablename} "
                    f"(a INTEGER PRIMARY KEY, b INTEGER)"
                )
            )
            con.execute(
                text(
                    f"INSERT INTO {self.tablename} "
                    f"({self.a}, {self.b}) "
                    f"VALUES ({self.a_val1}, {self.b_val1})"
                )
            )
            con.execute(
                text(
                    f"INSERT INTO {self.tablename} "
                    f"({self.a}, {self.b}) "
                    f"VALUES ({self.a_val2}, {self.b_val2})"
                )
            )
        self.session = sessionmaker(
            bind=self.engine, future=True
        )()  # type: Session
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)
        self.table = self.metadata.tables[self.tablename]

    # noinspection DuplicatedCode
    def test_get_rows_fieldnames_from_raw_sql(self) -> None:
        sql = f"SELECT {self.a}, {self.b} FROM {self.tablename}"
        rows, fieldnames = get_rows_fieldnames_from_raw_sql(self.session, sql)
        self.assertEqual(fieldnames, [self.a, self.b])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], (self.a_val1, self.b_val1))
        self.assertEqual(rows[1], (self.a_val2, self.b_val2))

    # noinspection DuplicatedCode
    def test_get_rows_fieldnames_from_select(self) -> None:
        query = select(self.table.c.a, self.table.c.b).select_from(self.table)
        rows, fieldnames = get_rows_fieldnames_from_select(self.session, query)
        self.assertEqual(fieldnames, [self.a, self.b])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], (self.a_val1, self.b_val1))
        self.assertEqual(rows[1], (self.a_val2, self.b_val2))

    def test_count_star_and_max(self) -> None:
        count, maximum = count_star_and_max(
            self.session, self.tablename, self.b
        )
        self.assertEqual(count, 2)
        self.assertEqual(maximum, self.b_val2)

    def test_exists_in_table(self) -> None:
        exists1 = exists_in_table(self.session, self.table)
        self.assertTrue(exists1)
        exists2 = exists_in_table(
            self.session, self.table, column(self.a) == 1
        )
        self.assertTrue(exists2)

    def test_exists_plain(self) -> None:
        exists1 = exists_plain(self.session, self.tablename)
        self.assertTrue(exists1)
        exists2 = exists_plain(
            self.session, self.tablename, column(self.a) == 1
        )
        self.assertTrue(exists2)

    def test_fetch_all_first_values(self) -> None:
        select_stmt = select(text("*")).select_from(table(self.tablename))
        firstvalues = fetch_all_first_values(self.session, select_stmt)
        self.assertEqual(len(firstvalues), 2)
        self.assertEqual(firstvalues, [self.a_val1, self.a_val2])
