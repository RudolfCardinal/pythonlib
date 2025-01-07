#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/tests/merge_db_tests.py

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

import unittest

from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.orm.session import Session, sessionmaker
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import Integer, Text

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler
from cardinal_pythonlib.sqlalchemy.merge_db import merge_db
from cardinal_pythonlib.sqlalchemy.session import SQLITE_MEMORY_URL

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Unit tests
# =============================================================================

Base = declarative_base()


class Parent(Base):
    __tablename__ = "parent"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text)


class Child(Base):
    __tablename__ = "child"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text)
    parent_id = Column(Integer, ForeignKey("parent.id"))
    parent = relationship(Parent)


class MergeTestMixin(object):
    """
    Mixin to create source/destination databases as in-memory SQLite databases
    for unit testing purposes.
    """

    def setUp(self) -> None:
        super().setUp()

        self.src_engine = create_engine(
            SQLITE_MEMORY_URL, future=True
        )  # type: Engine
        self.dst_engine = create_engine(
            SQLITE_MEMORY_URL, future=True
        )  # type: Engine
        self.src_session = sessionmaker(
            bind=self.src_engine
        )()  # type: Session
        self.dst_session = sessionmaker(
            bind=self.dst_engine
        )()  # type: Session

    def do_merge(self, dummy_run: bool = False) -> None:
        merge_db(
            base_class=Base,
            src_engine=self.src_engine,
            dst_session=self.dst_session,
            allow_missing_src_tables=False,
            allow_missing_src_columns=True,
            translate_fn=None,
            skip_tables=None,
            only_tables=None,
            extra_table_dependencies=None,
            dummy_run=dummy_run,
            report_every=1000,
        )


class MergeTestPlain(MergeTestMixin, unittest.TestCase):
    """
    Unit tests for a simple merge operation.

    *Notes re unit testing:*

    - tests are found by virtue of the fact that their names start with
      "test"; see
      https://docs.python.org/3.6/library/unittest.html#basic-example

    - A separate instance of the class is created for each test, and in each
      case is called with:

      .. code-block:: python

        setUp()
        testSOMETHING()
        tearDown()

      ... see https://docs.python.org/3.6/library/unittest.html#test-cases

    - If you use mixins, they go AFTER :class:`unittest.TestCase`; see
      https://stackoverflow.com/questions/1323455/python-unit-test-with-base-and-sub-class

    """  # noqa: E501

    def setUp(self) -> None:
        super().setUp()

        Base.metadata.create_all(self.src_engine)
        Base.metadata.create_all(self.dst_engine)

        p1 = Parent(name="Parent 1")
        p2 = Parent(name="Parent 2")
        c1 = Child(name="Child 1")
        c2 = Child(name="Child 2")
        c1.parent = p1
        c2.parent = p2
        self.src_session.add_all([p1, p2, c1, c2])
        self.src_session.commit()

    def test_dummy_run_makes_no_changes(self) -> None:
        log.info("Testing merge_db() in dummy run mode")
        parents_before = self.dst_session.query(Parent).count()
        children_before = self.dst_session.query(Child).count()
        self.do_merge(dummy_run=True)
        self.dst_session.commit()
        parents_after = self.dst_session.query(Parent).count()
        children_after = self.dst_session.query(Child).count()
        self.assertEqual(parents_before, parents_after)
        self.assertEqual(children_before, children_after)

    def test_merge_to_empty_destination_copies_source(self) -> None:
        log.info("Testing merge_db() to empty database")

        destination_parents = self.dst_session.query(Parent).count()
        destination_children = self.dst_session.query(Child).count()
        self.assertEqual(destination_parents, 0)
        self.assertEqual(destination_children, 0)

        self.do_merge(dummy_run=False)
        self.dst_session.commit()

        destination_parents = self.dst_session.query(Parent).count()
        destination_children = self.dst_session.query(Child).count()
        source_parents = self.src_session.query(Parent).count()
        source_children = self.src_session.query(Child).count()
        self.assertEqual(source_parents, destination_parents)
        self.assertEqual(source_children, destination_children)

    def test_merge_to_existing(self) -> None:
        log.info("Testing merge_db() to pre-populated database")
        self.do_merge(dummy_run=False)
        self.dst_session.commit()
        self.do_merge(dummy_run=False)
        self.dst_session.commit()

        destination_parents = self.dst_session.query(Parent).count()
        destination_children = self.dst_session.query(Child).count()
        source_parents = self.src_session.query(Parent).count()
        source_children = self.src_session.query(Child).count()

        self.assertEqual(destination_parents, source_parents * 2)
        self.assertEqual(destination_children, source_children * 2)
