#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/tests/orm_query_tests.py

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

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.schema import Column
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.sqltypes import Integer, String

from cardinal_pythonlib.sqlalchemy.core_query import (
    get_rows_fieldnames_from_select,
)
from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName
from cardinal_pythonlib.sqlalchemy.orm_query import (
    CountStarSpecializedQuery,
    bool_from_exists_clause,
    exists_orm,
    get_or_create,
    get_rows_fieldnames_from_query,
)
from cardinal_pythonlib.sqlalchemy.session import SQLITE_MEMORY_URL

log = logging.getLogger(__name__)


# =============================================================================
# SQLAlchemy test framework
# =============================================================================

Base = declarative_base()


class Person(Base):
    __tablename__ = "person"
    pk = Column("pk", Integer, primary_key=True, autoincrement=True)
    name = Column("name", Integer, index=True)
    address = Column("address", Integer, index=False)


class Pet(Base):
    __tablename__ = "pet"
    id = Column("id", Integer, primary_key=True)
    name = Column("name", String(50))


# =============================================================================
# Unit tests
# =============================================================================


class OrmQueryTests(TestCase):
    def __init__(self, *args, echo: bool = False, **kwargs) -> None:
        self.echo = echo
        super().__init__(*args, **kwargs)

    def setUp(self) -> None:
        self.engine = create_engine(
            SQLITE_MEMORY_URL, echo=self.echo, future=True
        )
        self.session = sessionmaker(bind=self.engine)()  # for ORM
        Base.metadata.create_all(bind=self.engine)
        self._pet_1_name = "Garfield"
        self.pet1 = Pet(id=1, name=self._pet_1_name)
        self.session.add(self.pet1)
        self.session.flush()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_rows_fieldnames_from_select
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_get_rows_fieldnames_old_function_fails(self) -> None:
        # Superseded
        query = select(Pet.id, Pet.name).select_from(Pet.__table__)
        with self.assertRaises(NotImplementedError):
            get_rows_fieldnames_from_query(self.session, query)

    def test_get_rows_fieldnames_old_style_fails(self) -> None:
        # Wrong type of object
        query = self.session.query(Pet)
        with self.assertRaises(ValueError):
            get_rows_fieldnames_from_select(self.session, query)

    def test_get_rows_fieldnames_select_works(self) -> None:
        # How it should be done in SQLAlchemy 2: select(), either with ORM
        # classes or columns/column-like things.
        query = select(Pet.id, Pet.name).select_from(Pet.__table__)
        rows, fieldnames = get_rows_fieldnames_from_select(self.session, query)
        self.assertEqual(fieldnames, ["id", "name"])
        self.assertEqual(rows, [(1, self._pet_1_name)])

    def test_get_rows_fieldnames_whole_object_q_fails(self) -> None:
        # We want to disallow querying
        query = select(Pet)
        with self.assertRaises(ValueError):
            get_rows_fieldnames_from_select(self.session, query)

    def test_get_rows_fieldnames_no_rows_returns_fieldnames(self) -> None:
        # Check zero-result queries still give fieldnames
        query = select(Pet.id, Pet.name).where(Pet.name == "missing")
        rows, fieldnames = get_rows_fieldnames_from_select(self.session, query)
        self.assertEqual(fieldnames, ["id", "name"])
        self.assertEqual(rows, [])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # bool_from_exists_clause
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_bool_from_exists_clause_sqlite(self) -> None:
        exists_q = self.session.query(Pet).exists()
        b = bool_from_exists_clause(self.session, exists_q)
        self.assertIsInstance(b, bool)

    def test_bool_from_exists_clause_sqlite_pretending_mysql(self) -> None:
        self.session.get_bind().dialect.name = SqlaDialectName.MSSQL
        # NB setUp() is called for each test, so this won't break others
        exists_q = self.session.query(Pet).exists()
        b = bool_from_exists_clause(self.session, exists_q)
        self.assertIsInstance(b, bool)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # exists_orm
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_exists_orm_when_exists(self) -> None:
        b = exists_orm(self.session, Pet)
        self.assertIsInstance(b, bool)
        self.assertEqual(b, True)

    def test_exists_orm_when_not_exists(self) -> None:
        b = exists_orm(self.session, Person)
        self.assertIsInstance(b, bool)
        self.assertEqual(b, False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_or_create
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_get_or_create_get(self) -> None:
        p, newly_created = get_or_create(self.session, Pet, id=1)
        self.assertIsInstance(p, Pet)
        self.assertIsInstance(newly_created, bool)
        self.assertEqual(p.id, 1)
        self.assertEqual(p.name, self._pet_1_name)
        self.assertEqual(newly_created, False)

    def test_get_or_create_create(self) -> None:
        newid = 3
        newname = "Nermal"
        p, newly_created = get_or_create(
            self.session, Pet, id=newid, name=newname
        )
        self.assertIsInstance(p, Pet)
        self.assertIsInstance(newly_created, bool)
        self.assertEqual(p.id, newid)
        self.assertEqual(p.name, newname)
        self.assertEqual(newly_created, True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CountStarSpecializedQuery
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_count_star_specialized_one(self) -> None:
        # echo output also inspected
        q = CountStarSpecializedQuery(Pet, session=self.session)
        n = q.count_star()
        self.assertIsInstance(n, int)
        self.assertEqual(n, 1)

    def test_count_star_specialized_none(self) -> None:
        # echo output also inspected
        q = CountStarSpecializedQuery(Person, session=self.session)
        n = q.count_star()
        self.assertIsInstance(n, int)
        self.assertEqual(n, 0)

    def test_count_star_specialized_filter(self) -> None:
        # echo output also inspected
        q = CountStarSpecializedQuery(Pet, session=self.session).filter(
            Pet.name == self._pet_1_name
        )
        n = q.count_star()
        self.assertIsInstance(n, int)
        self.assertEqual(n, 1)
