#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/tests/dump_tests.py

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

import logging
import unittest

from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm.session import Session, sessionmaker
from sqlalchemy.schema import Column, MetaData, Table
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.sqltypes import Integer, String

from cardinal_pythonlib.sqlalchemy.dump import (
    get_literal_query,
    make_literal_query_fn,
)
from cardinal_pythonlib.sqlalchemy.session import SQLITE_MEMORY_URL

log = logging.getLogger(__name__)

Base = declarative_base()


# =============================================================================
# Unit tests
# =============================================================================


def simplify_whitespace(statement: str) -> str:
    """
    Standardize SQL by simplifying whitespace.
    """
    return statement.replace("\n", " ").replace("  ", " ")


class DumpTests(unittest.TestCase):
    """
    Test some of our custom SQL dump functions.
    """

    def __init__(self, *args, echo: bool = False, **kwargs) -> None:
        self.echo = echo
        super().__init__(*args, **kwargs)

    class Person(Base):
        __tablename__ = "person"
        pk = Column("pk", Integer, primary_key=True, autoincrement=True)
        name = Column("name", Integer, index=True)
        address = Column("address", Integer, index=False)

    def setUp(self) -> None:
        super().setUp()

        self.engine = create_engine(
            SQLITE_MEMORY_URL, echo=self.echo
        )  # type: Engine
        self.dialect = self.engine.dialect
        self.session = sessionmaker(bind=self.engine)()  # type: Session
        self.metadata = MetaData()

        self.pet = Table(
            "pet",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
        )

    def test_literal_query_method_1_base(self) -> None:
        namecol = self.pet.columns.name
        base_q = select(namecol).where(namecol == "Garfield")
        literal_query = make_literal_query_fn(self.dialect)
        literal = simplify_whitespace(literal_query(base_q))
        self.assertEqual(
            literal, "SELECT pet.name FROM pet WHERE pet.name = 'Garfield';"
        )

    def test_literal_query_method_1_orm(self) -> None:
        orm_q = select(self.Person.name).where(self.Person.name == "Jon")
        literal_query = make_literal_query_fn(self.dialect)
        literal = simplify_whitespace(literal_query(orm_q))
        self.assertEqual(
            literal,
            "SELECT person.name FROM person WHERE person.name = 'Jon';",
        )

    def test_literal_query_method_2_base(self) -> None:
        namecol = self.pet.columns.name
        base_q = select(namecol).where(namecol == "Garfield")
        literal = simplify_whitespace(
            get_literal_query(base_q, bind=self.engine)
        )
        self.assertEqual(
            literal, "SELECT pet.name FROM pet WHERE pet.name = 'Garfield';"
        )

    def test_literal_query_method_2_orm(self) -> None:
        orm_q = select(self.Person.pk).where(self.Person.name == "Jon")
        literal = simplify_whitespace(
            get_literal_query(orm_q, bind=self.engine)
        )
        self.assertEqual(
            literal, "SELECT person.pk FROM person WHERE person.name = 'Jon';"
        )
