#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/tests/orm_schema_tests.py

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
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import Integer, String

from cardinal_pythonlib.sqlalchemy.orm_schema import (
    create_table_from_orm_class,
)
from cardinal_pythonlib.sqlalchemy.session import SQLITE_MEMORY_URL

log = logging.getLogger(__name__)


# =============================================================================
# SQLAlchemy test framework
# =============================================================================

Base = declarative_base()


class Pet(Base):
    __tablename__ = "pet"
    id = Column("id", Integer, primary_key=True)
    name = Column("name", String(50))


# =============================================================================
# Unit tests
# =============================================================================


class OrmQueryTests(TestCase):
    def __init__(self, *args, echo: bool = True, **kwargs) -> None:
        self.echo = echo
        super().__init__(*args, **kwargs)

    def setUp(self) -> None:
        self.engine = create_engine(
            SQLITE_MEMORY_URL, echo=self.echo, future=True
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # create_table_from_orm_class
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def test_create_table_from_orm_class(self) -> None:
        create_table_from_orm_class(self.engine, Pet)
