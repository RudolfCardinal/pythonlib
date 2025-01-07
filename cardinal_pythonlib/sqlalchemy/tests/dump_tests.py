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
from io import StringIO
import re
import unittest

from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm.session import Session, sessionmaker
from sqlalchemy.schema import Column, Table
from sqlalchemy.sql.expression import select, text
from sqlalchemy.sql.sqltypes import Integer, String

from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName
from cardinal_pythonlib.sqlalchemy.dump import (
    dump_connection_info,
    dump_ddl,
    dump_table_as_insert_sql,
    get_literal_query,
    make_literal_query_fn,
    COMMENT_SEP1,
    COMMENT_SEP2,
)
from cardinal_pythonlib.sqlalchemy.session import SQLITE_MEMORY_URL

log = logging.getLogger(__name__)


# =============================================================================
# Helper functions
# =============================================================================


def simplify_whitespace(statement: str) -> str:
    """
    Standardize SQL by simplifying whitespace.
    """
    x = statement.replace("\n", " ").replace("\t", " ")
    x = re.sub(" +", " ", x)  # replace multiple spaces with single space
    return x.strip()


# =============================================================================
# SQLAlchemy test framework
# =============================================================================

Base = declarative_base()


class Person(Base):
    __tablename__ = "person"
    pk = Column("pk", Integer, primary_key=True, autoincrement=True)
    name = Column("name", Integer, index=True)
    address = Column("address", Integer, index=False)


PET_TABLE = Table(
    "pet",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(50)),
)


# =============================================================================
# Unit tests
# =============================================================================


class DumpTests(unittest.TestCase):
    """
    Test some of our custom SQL dump functions.
    """

    def __init__(self, *args, echo: bool = False, **kwargs) -> None:
        self.echo = echo
        super().__init__(*args, **kwargs)

    def setUp(self) -> None:
        # NB This function gets executed for each test. Therefore, don't set
        # up tables here using a class-specific metadata.
        super().setUp()

        self.engine = create_engine(
            SQLITE_MEMORY_URL, echo=self.echo, future=True
        )  # type: Engine
        self.dialect = self.engine.dialect
        self.session = sessionmaker(bind=self.engine)()  # type: Session

        Base.metadata.create_all(bind=self.engine)
        with self.engine.begin() as connection:
            connection.execute(
                text("INSERT INTO pet (id, name) VALUES (1, 'Garfield')")
            )

    def test_literal_query_method_1_base(self) -> None:
        namecol = PET_TABLE.columns.name
        base_q = select(namecol).where(namecol == "Garfield")
        literal_query = make_literal_query_fn(self.dialect)
        literal = simplify_whitespace(literal_query(base_q))
        self.assertEqual(
            literal, "SELECT pet.name FROM pet WHERE pet.name = 'Garfield';"
        )

    def test_literal_query_method_1_orm(self) -> None:
        orm_q = select(Person.name).where(Person.name == "Jon")
        literal_query = make_literal_query_fn(self.dialect)
        literal = simplify_whitespace(literal_query(orm_q))
        self.assertEqual(
            literal,
            "SELECT person.name FROM person WHERE person.name = 'Jon';",
        )

    def test_literal_query_method_2_base(self) -> None:
        namecol = PET_TABLE.columns.name
        base_q = select(namecol).where(namecol == "Garfield")
        literal = simplify_whitespace(
            get_literal_query(base_q, bind=self.engine)
        )
        self.assertEqual(
            literal, "SELECT pet.name FROM pet WHERE pet.name = 'Garfield';"
        )

    def test_literal_query_method_2_orm(self) -> None:
        orm_q = select(Person.pk).where(Person.name == "Jon")
        literal = simplify_whitespace(
            get_literal_query(orm_q, bind=self.engine)
        )
        self.assertEqual(
            literal, "SELECT person.pk FROM person WHERE person.name = 'Jon';"
        )

    def test_dump_connection_info(self) -> None:
        s = StringIO()
        dump_connection_info(engine=self.engine, fileobj=s)
        txt = simplify_whitespace(s.getvalue())
        self.assertEqual(txt, f"-- Database info: {SQLITE_MEMORY_URL}")

    def test_dump_ddl(self) -> None:
        s = StringIO()
        dump_ddl(
            metadata=Base.metadata,
            dialect_name=SqlaDialectName.SQLITE,
            fileobj=s,
        )
        txt = simplify_whitespace(s.getvalue())
        self.assertEqual(
            txt,
            "-- Schema (for dialect sqlite): "
            "CREATE TABLE person ( "
            "pk INTEGER NOT NULL, "
            "name INTEGER, "
            "address INTEGER, "
            "PRIMARY KEY (pk) "
            ") "
            "; "
            "CREATE INDEX ix_person_name ON person (name); "
            "CREATE TABLE pet ( "
            "id INTEGER NOT NULL, "
            "name VARCHAR(50), "
            "PRIMARY KEY (id) "
            ") "
            ";",
        )

    def test_dump_table_as_insert_sql(self) -> None:
        s = StringIO()
        dump_table_as_insert_sql(
            engine=self.engine, table_name="pet", fileobj=s, include_ddl=False
        )
        txt = simplify_whitespace(s.getvalue())
        self.assertEqual(
            txt,
            f"{COMMENT_SEP1} "
            f"-- Data for table: pet "
            f"{COMMENT_SEP2} "
            f"-- Filters: None "
            f"INSERT INTO pet (id, name) VALUES (1, 'Garfield'); "
            f"{COMMENT_SEP2}",
        )
