#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/tests/orm_inspect_tests.py

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

"""

from typing import Tuple
import unittest

from sqlalchemy.orm import declarative_base
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Integer

from cardinal_pythonlib.sqlalchemy.orm_inspect import gen_columns

Base = declarative_base()


class Person(Base):
    __tablename__ = "person"
    pk_attr = Column("pk", Integer, primary_key=True, autoincrement=True)
    name_attr = Column("name", Integer)


class GenColumnsTests(unittest.TestCase):
    def assert_column(
        self, column_info: Tuple[str, Column], attr_name: str, column_name: str
    ) -> None:
        self.assertEqual(column_info[0], attr_name)
        self.assertIsInstance(column_info[1], Column)
        self.assertEqual(column_info[1].name, column_name)

    def test_all_columns_returned_for_instance(self) -> None:
        person = Person()

        columns = list(gen_columns(person))

        self.assert_column(columns[0], "pk_attr", "pk")
        self.assert_column(columns[1], "name_attr", "name")

    def test_all_columns_returned_for_class(self) -> None:
        columns = list(gen_columns(Person))

        self.assert_column(columns[0], "pk_attr", "pk")
        self.assert_column(columns[1], "name_attr", "name")
