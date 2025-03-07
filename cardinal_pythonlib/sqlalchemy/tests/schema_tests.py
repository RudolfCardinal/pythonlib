#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/tests/schema_tests.py

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
import sys

from sqlalchemy import event, inspect, select
from sqlalchemy.dialects.mssql.base import MSDialect, DECIMAL as MS_DECIMAL
from sqlalchemy.dialects.mysql.base import MySQLDialect
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import NoSuchTableError, OperationalError
from sqlalchemy.ext import compiler
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from sqlalchemy.schema import (
    Column,
    CreateTable,
    DDL,
    DDLElement,
    Index,
    MetaData,
    Sequence,
    Table,
)
from sqlalchemy.sql import table
from sqlalchemy.sql.selectable import Select
from sqlalchemy.sql.sqltypes import (
    BigInteger,
    Date,
    DateTime,
    Float,
    LargeBinary,
    Integer,
    String,
    Text,
    Time,
)

from cardinal_pythonlib.sqlalchemy.engine_func import (
    get_dialect_name,
    SqlaDialectName,
)
from cardinal_pythonlib.sqlalchemy.schema import (
    add_index,
    column_creation_ddl,
    column_lists_equal,
    column_types_equal,
    columns_equal,
    convert_sqla_type_for_dialect,
    does_sqlatype_require_index_len,
    execute_ddl,
    gen_columns_info,
    get_column_info,
    get_column_names,
    get_column_type,
    get_effective_int_pk_col,
    get_list_of_sql_string_literals_from_quoted_csv,
    get_pk_colnames,
    get_single_int_autoincrement_colname,
    get_single_int_pk_colname,
    get_sqla_coltype_from_dialect_str,
    get_table_names,
    get_view_names,
    index_exists,
    is_sqlatype_binary,
    is_sqlatype_date,
    is_sqlatype_integer,
    is_sqlatype_numeric,
    is_sqlatype_string,
    is_sqlatype_text_of_length_at_least,
    is_sqlatype_text_over_one_char,
    make_bigint_autoincrement_column,
    mssql_get_pk_index_name,
    mssql_table_has_ft_index,
    mssql_transaction_count,
    remove_collation,
    table_exists,
    table_or_view_exists,
    view_exists,
)
from cardinal_pythonlib.sqlalchemy.session import SQLITE_MEMORY_URL
from cardinal_pythonlib.sqlalchemy.sqlserver import (
    if_sqlserver_disable_constraints,
)

Base = declarative_base()
log = logging.getLogger(__name__)


# =============================================================================
# NOT TESTED from schema.py:
# =============================================================================
# giant_text_sqltype
# does_sqlatype_merit_fulltext_index (see is_sqlatype_text_of_length_at_least)
# indexes_equal
# index_lists_equal


# =============================================================================
# Tests
# =============================================================================


class SchemaTests(unittest.TestCase):
    def test_schema_functions(self) -> None:
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # make_bigint_autoincrement_column
        # column_creation_ddl
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        d_mssql = MSDialect()
        d_mysql = MySQLDialect()
        big_int_null_col = Column("hello", BigInteger, nullable=True)
        big_int_autoinc_col = Column("world", BigInteger, autoincrement=True)
        # ... used NOT to generate IDENTITY, but now does (2022-02-26, with
        #     SQLAlchemy==1.3.18)
        big_int_autoinc_sequence_col = make_bigint_autoincrement_column(
            "you", d_mssql
        )
        metadata = MetaData()
        t = Table("mytable", metadata)
        t.append_column(big_int_null_col)
        t.append_column(big_int_autoinc_col)
        t.append_column(big_int_autoinc_sequence_col)

        log.info("Checking Column -> DDL: SQL Server (mssql)")
        self.assertEqual(
            column_creation_ddl(big_int_null_col, d_mssql), "hello BIGINT NULL"
        )
        self.assertEqual(
            column_creation_ddl(big_int_autoinc_col, d_mssql),
            # IDENTITY without any arguments is the same as IDENTITY(1,1)
            "world BIGINT NOT NULL IDENTITY",
        )

        self.assertEqual(
            column_creation_ddl(big_int_autoinc_sequence_col, d_mssql),
            "you BIGINT NOT NULL IDENTITY(1,1)",
        )

        log.info("Checking Column -> DDL: MySQL (mysql)")
        self.assertEqual(
            column_creation_ddl(big_int_null_col, d_mysql), "hello BIGINT"
        )
        self.assertEqual(
            column_creation_ddl(big_int_autoinc_col, d_mysql), "world BIGINT"
        )
        # not big_int_autoinc_sequence_col; not supported by MySQL

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # get_sqla_coltype_from_dialect_str
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        log.info("Checking SQL type -> SQL Alchemy type")
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
            log.info(
                f"... {coltype!r} -> dialect {dialect.name!r} -> "
                f"{get_sqla_coltype_from_dialect_str(coltype, dialect)!r}"
            )


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# index_exists
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class IndexExistsTests(unittest.TestCase):
    def __init__(self, *args, echo: bool = False, **kwargs) -> None:
        self.echo = echo
        super().__init__(*args, **kwargs)

    def setUp(self) -> None:
        super().setUp()
        self.engine = create_engine(
            SQLITE_MEMORY_URL, echo=self.echo, future=True
        )
        metadata = MetaData()
        self.person = Table(
            "person",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), index=True),
            Column("address", String(50)),
            Index("my_index2", "id", "name"),
        )
        # Expected indexes, therefore:
        # 1. "ix_person_name" (by default naming convention) on person.name
        # 2. "my_index2" on {person.id, person.name}
        with self.engine.begin() as conn:
            metadata.create_all(conn)

    def test_bad_table(self) -> None:
        with self.assertRaises(NoSuchTableError):
            index_exists(
                self.engine,
                "nonexistent_table",
                "does_not_matter",
                raise_if_nonexistent_table=True,
            )

    def test_exists(self) -> None:
        # First index:
        self.assertTrue(index_exists(self.engine, "person", colnames="name"))
        self.assertTrue(index_exists(self.engine, "person", colnames=["name"]))
        # And by the default naming convention:
        self.assertTrue(
            index_exists(self.engine, "person", indexname="ix_person_name")
        )
        # Second index:
        self.assertTrue(
            index_exists(self.engine, "person", colnames=["id", "name"])
        )
        self.assertTrue(
            index_exists(self.engine, "person", indexname="my_index2")
        )

    def test_does_not_exist(self) -> None:
        self.assertFalse(index_exists(self.engine, "person", indexname="name"))
        self.assertFalse(
            index_exists(self.engine, "person", colnames="address")
        )
        self.assertFalse(
            index_exists(self.engine, "person", colnames=["name", "address"])
        )


# -----------------------------------------------------------------------------
# Support code for view testing
# -----------------------------------------------------------------------------


# https://github.com/sqlalchemy/sqlalchemy/wiki/Views
class CreateView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    def __init__(self, name):
        self.name = name


# noinspection PyUnusedLocal
@compiler.compiles(CreateView)
def _create_view(element, compiler_, **kw):
    return "CREATE VIEW %s AS %s" % (
        element.name,
        compiler_.sql_compiler.process(element.selectable, literal_binds=True),
    )


# noinspection PyUnusedLocal
@compiler.compiles(DropView)
def _drop_view(element, compiler_, **kw) -> str:
    return "DROP VIEW %s" % element.name


# noinspection PyUnusedLocal
def _view_exists(ddl, target, connection, **kw) -> bool:
    return ddl.name in inspect(connection).get_view_names()


def _view_doesnt_exist(ddl, target, connection, **kw):
    return not _view_exists(ddl, target, connection, **kw)


def _attach_view(
    tablename: str, metadata: MetaData, selectable: Select
) -> None:
    """
    Attaches a view to a table of the given name, such that the view (which is
    of "selectable") is created after the table is created, and dropped before
    the table is dropped, via listeners.
    """
    t = table(
        tablename,
        *(
            Column(c.name, c.type, primary_key=c.primary_key)
            for c in selectable.selected_columns
        ),
    )
    t.primary_key.update(c for c in t.c if c.primary_key)

    event.listen(
        metadata,
        "after_create",
        CreateView(tablename, selectable).execute_if(
            callable_=_view_doesnt_exist
        ),
    )
    event.listen(
        metadata,
        "before_drop",
        DropView(tablename).execute_if(callable_=_view_exists),
    )


class MoreSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.engine = create_engine(SQLITE_MEMORY_URL, future=True)
        metadata = MetaData()

        self.person = Table(
            "person",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
        )

        _attach_view(
            "one",
            metadata,
            select(self.person.c.id.label("name")),
        )
        _attach_view(
            "two",
            metadata,
            select(self.person.c.id.label("name")),
        )
        _attach_view(
            "three",
            metadata,
            select(self.person.c.id.label("name")),
        )

        with self.engine.begin() as conn:
            metadata.create_all(conn)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_table_names
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_table_names(self) -> None:
        table_names = get_table_names(self.engine)
        self.assertEqual(len(table_names), 1)
        self.assertIn("person", table_names)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_view_names
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_view_names(self) -> None:
        view_names = get_view_names(self.engine)
        self.assertEqual(len(view_names), 3)
        self.assertIn("one", view_names)
        self.assertIn("two", view_names)
        self.assertIn("three", view_names)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # table_exists
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_table_exists(self) -> None:
        self.assertTrue(table_exists(self.engine, "person"))
        self.assertFalse(table_exists(self.engine, "nope"))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # view_exists
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_view_exists(self) -> None:
        self.assertTrue(view_exists(self.engine, "one"))
        self.assertFalse(view_exists(self.engine, "nope"))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # table_or_view_exists
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_table_or_view_exists(self) -> None:
        self.assertTrue(table_or_view_exists(self.engine, "person"))  # table
        self.assertTrue(table_or_view_exists(self.engine, "one"))  # view
        self.assertFalse(table_or_view_exists(self.engine, "nope"))

    def test_get_column_info(self) -> None:
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # gen_columns_info
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ci_list = list(gen_columns_info(self.engine, "person"))
        self.assertEqual(len(ci_list), 2)
        ci_id = ci_list[0]
        self.assertEqual(ci_id.name, "id")
        self.assertIsInstance(ci_id.type, Integer)
        self.assertEqual(ci_id.nullable, False)
        self.assertEqual(ci_id.default, None)
        self.assertEqual(ci_id.attrs, {})
        self.assertEqual(ci_id.comment, "")

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # get_column_info
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ci_id_2 = get_column_info(self.engine, "person", "id")
        for a in ("name", "nullable", "default", "attrs", "comment"):
            self.assertEqual(getattr(ci_id_2, a), getattr(ci_id, a))
        self.assertEqual(type(ci_id_2.type), type(ci_id.type))

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # get_column_type
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ci_id_3_type = get_column_type(self.engine, "person", "id")
        self.assertEqual(type(ci_id_3_type), type(ci_id.type))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # table_or_view_exists
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_column_names(self) -> None:
        colnames = get_column_names(self.engine, "person")
        self.assertEqual(colnames, ["id", "name"])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_pk_colnames
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_pk_colnames(self) -> None:
        pknames = get_pk_colnames(self.person)
        self.assertEqual(pknames, ["id"])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_single_int_pk_colname
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_single_int_pk_colname(self) -> None:
        pkname = get_single_int_pk_colname(self.person)
        self.assertEqual(pkname, "id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_single_int_autoincrement_colname (partial test)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_single_int_autoincrement_colname_a(self) -> None:
        pkname = get_single_int_autoincrement_colname(self.person)
        self.assertEqual(pkname, "id")
        # This is present based on SQLAlchemy's default "auto" and its
        # semantics for integer PKs. See below for one where it's forced off.

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_effective_int_pk_col
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_effective_int_pk_col(self) -> None:
        pkname = get_effective_int_pk_col(self.person)
        self.assertEqual(pkname, "id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # mssql_get_pk_index_name (partial test)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_mssql_get_pk_index_name(self) -> None:
        with self.assertRaises(OperationalError):
            # Bad SQL for SQLite. But should not raise NotImplementedError,
            # which is what happens with query methods incompatible with
            # SQLAlchemy 2.0.
            mssql_get_pk_index_name(self.engine, "person")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # mssql_table_has_ft_index (partial test)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_mssql_table_has_ft_index(self) -> None:
        with self.assertRaises(OperationalError):
            # As above
            mssql_table_has_ft_index(self.engine, "person")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # mssql_transaction_count (partial test)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_mssql_transaction_count(self) -> None:
        with self.assertRaises(OperationalError):
            # As above
            mssql_transaction_count(self.engine)


class YetMoreSchemaTests(unittest.TestCase):
    def __init__(self, *args, echo: bool = True, **kwargs) -> None:
        self.echo = echo
        super().__init__(*args, **kwargs)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # make_bigint_autoincrement_column
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def setUp(self) -> None:
        super().setUp()
        self.engine = create_engine(
            SQLITE_MEMORY_URL, echo=self.echo, future=True
        )
        self.metadata = MetaData()
        self.person = Table(
            "person",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("name", String(50)),
            make_bigint_autoincrement_column("bigthing"),
        )
        with self.engine.begin() as conn:
            self.metadata.create_all(conn)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_single_int_autoincrement_colname (again)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_single_int_autoincrement_colname_b(self) -> None:
        pkname = get_single_int_autoincrement_colname(self.person)
        self.assertIsNone(pkname)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # add_index
    # indexes_equal
    # index_lists_equal
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_add_index(self) -> None:
        add_index(self.engine, self.person.columns.name)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # column_creation_ddl
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_column_creation_ddl(self) -> None:
        mssql_dialect = MSDialect()
        mysql_dialect = MySQLDialect()

        col1 = Column("hello", BigInteger, nullable=True)
        col2 = Column(
            "world", BigInteger, autoincrement=True
        )  # does NOT generate IDENTITY
        col3 = Column(
            "you", BigInteger, Sequence("dummy_name", start=1, increment=1)
        )

        self.metadata = MetaData()
        t = Table("mytable", self.metadata)
        t.append_column(col1)
        t.append_column(col2)
        t.append_column(col3)
        # See column_creation_ddl() for reasons for attaching to a Table.

        self.assertEqual(
            column_creation_ddl(col1, mssql_dialect),
            "hello BIGINT NULL",
        )
        self.assertEqual(
            column_creation_ddl(col2, mssql_dialect),
            "world BIGINT NOT NULL IDENTITY",
            # used to be "world BIGINT NULL"
        )
        self.assertEqual(
            column_creation_ddl(col3, mssql_dialect),
            "you BIGINT NOT NULL"
            # used to be "you BIGINT NOT NULL IDENTITY(1,1)",
        )

        self.assertEqual(
            column_creation_ddl(col1, mysql_dialect),
            "hello BIGINT",
        )
        self.assertEqual(
            column_creation_ddl(col2, mysql_dialect),
            "world BIGINT",
        )
        self.assertEqual(
            column_creation_ddl(col3, mysql_dialect), "you BIGINT"
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # remove_collation
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_remove_collation(self) -> None:
        remove_collation(self.person.columns.name)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # convert_sqla_type_for_dialect (very basic only!)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_convert_sqla_type_for_dialect(self) -> None:
        to_dialect = MySQLDialect()
        c1 = convert_sqla_type_for_dialect(self.person.columns.id, to_dialect)
        self.assertIsInstance(c1, Column)
        c2 = convert_sqla_type_for_dialect(
            self.person.columns.name, to_dialect
        )
        self.assertIsInstance(c2, Column)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # column_types_equal
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_column_types_equal(self) -> None:
        self.assertTrue(column_types_equal(self.person.c.id, self.person.c.id))
        self.assertFalse(
            column_types_equal(self.person.c.id, self.person.c.name)
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # column_types_equal
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_columns_equal(self) -> None:
        self.assertTrue(columns_equal(self.person.c.id, self.person.c.id))
        self.assertFalse(columns_equal(self.person.c.id, self.person.c.name))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # column_lists_equal
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_column_lists_equal(self) -> None:
        a = self.person.c.id
        b = self.person.c.name
        self.assertTrue(column_lists_equal([a, b], [a, b]))
        self.assertFalse(column_lists_equal([a, b], [b, a]))
        self.assertFalse(column_lists_equal([a, b], [a]))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # execute_ddl
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_execute_ddl(self) -> None:
        sql = "CREATE TABLE x (a INT)"
        execute_ddl(self.engine, sql=sql)

        ddl = CreateTable(Table("y", self.metadata, Column("z", Integer)))
        execute_ddl(self.engine, ddl=ddl)

        with self.assertRaises(AssertionError):
            execute_ddl(self.engine, sql=sql, ddl=ddl)  # both
        with self.assertRaises(AssertionError):
            execute_ddl(self.engine)  # neither

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Dialect conditionality for DDL
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _present_in_log_output(_cm, msg: str) -> bool:
        """
        Detects whether a string is present, INCLUDING AS A SUBSTRING, in
        log output captured from an assertLogs() context manager.
        """
        return any(msg in line for line in _cm.output)

    def test_ddl_dialect_conditionality_1(self) -> None:
        self.engine.echo = True  # will write to log at INFO level

        # 1. Check that logging capture works, and our _present_in_log_output
        # function.
        with self.assertLogs(level=logging.INFO) as cm:
            log.info("dummy call")
            self.assertTrue(self._present_in_log_output(cm, "dummy"))

        # 2. Check our dialect is as expected: SQLite.
        dialect_name = get_dialect_name(self.engine)
        self.assertEqual(dialect_name, SqlaDialectName.SQLITE)

        # 3. Seeing if DDL built with execute_if() will execute "directly" when
        # set to execute-if-SQLite. It executes - but not conditionally!
        ddl_yes = DDL("CREATE TABLE yesplease (a INT)").execute_if(
            dialect=SqlaDialectName.SQLITE
        )
        with self.assertLogs(level=logging.INFO) as cm:
            execute_ddl(self.engine, ddl=ddl_yes)
            self.assertTrue(
                self._present_in_log_output(cm, "CREATE TABLE yesplease")
            )

        # 4. Seeing if DDL built with execute_if() will execute "directly" when
        # set to execute-if-MySQL. It executes - therefore not conditionally!
        # I'd misunderstood this: it is NOT conditionally executed.
        ddl_no = DDL("CREATE TABLE nothanks (a INT)").execute_if(
            dialect=SqlaDialectName.MYSQL
        )
        with self.assertLogs(level=logging.INFO) as cm:
            execute_ddl(self.engine, ddl=ddl_no)
            self.assertTrue(
                self._present_in_log_output(cm, "CREATE TABLE nothanks")
            )
            # I'd thought this would be false, but it is true.

    def test_ddl_dialect_conditionality_2(self) -> None:
        # Therefore:
        self.engine.echo = True  # will write to log at INFO level
        # The test above (test_ddl_dialect_conditionality_1) proves that
        # this code will log something if SQL is emitted.

        session = sessionmaker(
            bind=self.engine, future=True
        )()  # type: Session

        if sys.version_info < (3, 10):
            log.warning(
                "Unable to use unittest.TestCase.assertNoLogs; "
                "needs Python 3.10; skipping test"
            )
            return
        with self.assertNoLogs(level=logging.INFO):
            with if_sqlserver_disable_constraints(session, tablename="person"):
                pass
            # Should do nothing, therefore emit no logs.


class SchemaAbstractTests(unittest.TestCase):
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get_list_of_sql_string_literals_from_quoted_csv
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_list_of_sql_string_literals_from_quoted_csv(self) -> None:
        self.assertEqual(
            get_list_of_sql_string_literals_from_quoted_csv("'a', 'b', 'c'"),
            ["a", "b", "c"],
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # is_sqlatype_binary
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_is_sqlatype_binary(self) -> None:
        self.assertTrue(is_sqlatype_binary(LargeBinary()))

        self.assertFalse(is_sqlatype_binary(Integer()))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # is_sqlatype_date
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_is_sqlatype_date(self) -> None:
        self.assertTrue(is_sqlatype_date(Date()))
        self.assertTrue(is_sqlatype_date(DateTime()))

        self.assertFalse(is_sqlatype_date(Integer()))
        self.assertFalse(is_sqlatype_date(Time()))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # is_sqlatype_integer
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_is_sqlatype_integer(self) -> None:
        self.assertTrue(is_sqlatype_integer(Integer()))

        self.assertFalse(is_sqlatype_integer(Float()))
        self.assertFalse(is_sqlatype_integer(Date()))
        self.assertFalse(is_sqlatype_integer(DateTime()))
        self.assertFalse(is_sqlatype_integer(Time()))
        self.assertFalse(is_sqlatype_integer(String()))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # is_sqlatype_numeric
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_is_sqlatype_numeric(self) -> None:
        self.assertTrue(is_sqlatype_numeric(Float()))
        self.assertTrue(is_sqlatype_numeric(MS_DECIMAL()))

        self.assertFalse(is_sqlatype_numeric(Integer()))  # False!

        self.assertFalse(is_sqlatype_numeric(Date()))
        self.assertFalse(is_sqlatype_numeric(DateTime()))
        self.assertFalse(is_sqlatype_numeric(Time()))
        self.assertFalse(is_sqlatype_numeric(String()))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # is_sqlatype_string
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_is_sqlatype_string(self) -> None:
        self.assertTrue(is_sqlatype_string(String()))
        self.assertTrue(is_sqlatype_string(Text()))

        self.assertFalse(is_sqlatype_string(Integer()))
        self.assertFalse(is_sqlatype_string(Float()))
        self.assertFalse(is_sqlatype_string(Date()))
        self.assertFalse(is_sqlatype_string(DateTime()))
        self.assertFalse(is_sqlatype_string(Time()))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # is_sqlatype_text_of_length_at_least
    # ... and thus the trivial function does_sqlatype_merit_fulltext_index
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_is_sqlatype_text_of_length_at_least(self) -> None:
        testlen = 5
        self.assertTrue(
            is_sqlatype_text_of_length_at_least(String(testlen), testlen)
        )
        self.assertTrue(
            is_sqlatype_text_of_length_at_least(String(testlen + 1), testlen)
        )
        self.assertTrue(is_sqlatype_text_of_length_at_least(Text(), testlen))

        self.assertFalse(
            is_sqlatype_text_of_length_at_least(String(testlen - 1), testlen)
        )
        self.assertFalse(
            is_sqlatype_text_of_length_at_least(Integer(), testlen)
        )
        self.assertFalse(is_sqlatype_text_of_length_at_least(Float(), testlen))
        self.assertFalse(is_sqlatype_text_of_length_at_least(Date(), testlen))
        self.assertFalse(
            is_sqlatype_text_of_length_at_least(DateTime(), testlen)
        )
        self.assertFalse(is_sqlatype_text_of_length_at_least(Time(), testlen))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # is_sqlatype_text_over_one_char
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_is_sqlatype_text_over_one_char(self) -> None:
        self.assertTrue(is_sqlatype_text_over_one_char(String(2)))
        self.assertTrue(is_sqlatype_text_over_one_char(Text()))

        self.assertFalse(is_sqlatype_text_over_one_char(String(1)))
        self.assertFalse(is_sqlatype_text_over_one_char(Integer()))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # does_sqlatype_require_index_len
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_does_sqlatype_require_index_len(self) -> None:
        self.assertTrue(does_sqlatype_require_index_len(Text()))
        self.assertTrue(does_sqlatype_require_index_len(LargeBinary()))

        self.assertFalse(does_sqlatype_require_index_len(String(1)))
        self.assertFalse(does_sqlatype_require_index_len(Integer()))
