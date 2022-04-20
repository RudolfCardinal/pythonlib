#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/tests/schema_tests.py

"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

from sqlalchemy.dialects.mssql.base import MSDialect
from sqlalchemy.dialects.mysql.base import MySQLDialect
from sqlalchemy.schema import Column, MetaData, Table
from sqlalchemy.sql.sqltypes import BigInteger

from cardinal_pythonlib.sqlalchemy.schema import (
    column_creation_ddl,
    get_sqla_coltype_from_dialect_str,
    make_bigint_autoincrement_column,
)


# =============================================================================
# Tests
# =============================================================================


class SchemaTests(unittest.TestCase):
    def test_schema_functions(self) -> None:
        d_mssql = MSDialect()
        d_mysql = MySQLDialect()
        col1 = Column("hello", BigInteger, nullable=True)
        col2 = Column("world", BigInteger, autoincrement=True)
        # ... used NOT to generate IDENTITY, but now does (2022-02-26, with
        #     SQLAlchemy==1.3.18)
        col3 = make_bigint_autoincrement_column("you", d_mssql)
        metadata = MetaData()
        t = Table("mytable", metadata)
        t.append_column(col1)
        t.append_column(col2)
        t.append_column(col3)

        print("Checking Column -> DDL: SQL Server (mssql)")
        self.assertEqual(
            column_creation_ddl(col1, d_mssql), "hello BIGINT NULL"
        )
        self.assertEqual(
            column_creation_ddl(col2, d_mssql),
            # Old:
            # "world BIGINT NULL"
            # New:
            "world BIGINT NOT NULL IDENTITY(1,1)",
        )
        self.assertEqual(
            column_creation_ddl(col3, d_mssql),
            "you BIGINT NOT NULL IDENTITY(1,1)",
        )

        print("Checking Column -> DDL: MySQL (mysql)")
        self.assertEqual(column_creation_ddl(col1, d_mysql), "hello BIGINT")
        self.assertEqual(column_creation_ddl(col2, d_mysql), "world BIGINT")
        # not col3; unsupported

        print("Checking SQL type -> SQL Alchemy type")
        to_check = [
            # mssql
            ("BIGINT", d_mssql),
            ("NVARCHAR(32)", d_mssql),
            ("NVARCHAR(MAX)", d_mssql),
            ('NVARCHAR(160) COLLATE "Latin1_General_CI_AS"', d_mssql),
            # mysql
            ("BIGINT", d_mssql),
            ("LONGTEXT", d_mysql),
            ("ENUM('red','green','blue')", d_mysql),
        ]
        for coltype, dialect in to_check:
            print(
                f"... {coltype!r} -> dialect {dialect.name!r} -> "
                f"{get_sqla_coltype_from_dialect_str(coltype, dialect)!r}"
            )
