#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/schema.py

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

**Functions to work with SQLAlchemy schemas (schemata) directly, via SQLAlchemy
Core.**

Functions that have to work with specific dialect information are marked
DIALECT-AWARE.

"""

import ast
import copy
import csv
from functools import lru_cache
import io
import re
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    Union,
    TYPE_CHECKING,
)

from sqlalchemy import inspect

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.dialects import postgresql, mssql, mysql, sqlite
from sqlalchemy.dialects.mssql.base import TIMESTAMP as MSSQL_TIMESTAMP
from sqlalchemy.schema import (
    Column,
    CreateColumn,
    DDL,
    Identity,
    Index,
    Table,
)
from sqlalchemy.sql import sqltypes, text
from sqlalchemy.sql.ddl import DDLElement
from sqlalchemy.sql.sqltypes import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Float,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    TypeEngine,
)
from sqlalchemy.sql.visitors import Visitable

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler
from cardinal_pythonlib.sqlalchemy.dialect import (
    quote_identifier,
    SqlaDialectName,
)
from cardinal_pythonlib.sqlalchemy.orm_inspect import coltype_as_typeengine

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import ReflectedIndex

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Constants
# =============================================================================

VisitableType = Type[Visitable]  # for SQLAlchemy 2.0

MIN_TEXT_LENGTH_FOR_FREETEXT_INDEX = 1000
MSSQL_DEFAULT_SCHEMA = "dbo"
POSTGRES_DEFAULT_SCHEMA = "public"

DATABRICKS_SQLCOLTYPE_TO_SQLALCHEMY_GENERIC = {
    # A bit nasty: https://github.com/databricks/databricks-sqlalchemy
    # Part of the reverse mapping is via
    #   from databricks.sqlalchemy import DatabricksDialect
    #   print(DatabricksDialect.colspecs)
    "BIGINT": BigInteger,
    "BOOLEAN": Boolean,
    "DATE": Date,
    "TIMESTAMP_NTZ": DateTime,
    "DOUBLE": Double,
    "FLOAT": Float,
    "INT": Integer,
    "DECIMAL": Numeric,
    "SMALLINT": SmallInteger,
    "STRING": Text,
}


# =============================================================================
# Inspect tables (SQLAlchemy Core)
# =============================================================================


def get_table_names(engine: Engine) -> List[str]:
    """
    Returns a list of database table names from the :class:`Engine`.
    """
    insp = inspect(engine)
    return insp.get_table_names()


def get_view_names(engine: Engine) -> List[str]:
    """
    Returns a list of database view names from the :class:`Engine`.
    """
    insp = inspect(engine)
    return insp.get_view_names()


def table_exists(engine: Engine, tablename: str) -> bool:
    """
    Does the named table exist in the database?
    """
    return tablename in get_table_names(engine)


def view_exists(engine: Engine, viewname: str) -> bool:
    """
    Does the named view exist in the database?
    """
    return viewname in get_view_names(engine)


def table_or_view_exists(engine: Engine, table_or_view_name: str) -> bool:
    """
    Does the named table/view exist (either as a table or as a view) in the
    database?
    """
    tables_and_views = get_table_names(engine) + get_view_names(engine)
    return table_or_view_name in tables_and_views


class SqlaColumnInspectionInfo(object):
    """
    Class to represent information from inspecting a database column.

    A clearer way of getting information than the plain ``dict`` that
    SQLAlchemy uses.
    """

    def __init__(self, sqla_info_dict: Dict[str, Any]) -> None:
        """
        Args:
            sqla_info_dict:
                see

                - https://docs.sqlalchemy.org/en/latest/core/reflection.html#sqlalchemy.engine.reflection.Inspector.get_columns
                - https://bitbucket.org/zzzeek/sqlalchemy/issues/4051/sqlalchemyenginereflectioninspectorget_col
        """  # noqa: E501
        # log.debug(repr(sqla_info_dict))
        self.name = sqla_info_dict["name"]  # type: str
        self.type = sqla_info_dict["type"]  # type: TypeEngine
        self.nullable = sqla_info_dict["nullable"]  # type: bool
        self.default = sqla_info_dict[
            "default"
        ]  # type: Optional[str]  # SQL string expression
        self.attrs = sqla_info_dict.get("attrs", {})  # type: Dict[str, Any]
        self.comment = sqla_info_dict.get("comment", "")
        # ... NB not appearing in


def gen_columns_info(
    engine: Engine, tablename: str
) -> Generator[SqlaColumnInspectionInfo, None, None]:
    """
    For the specified table, generate column information as
    :class:`SqlaColumnInspectionInfo` objects.
    """
    # Dictionary structure: see
    # http://docs.sqlalchemy.org/en/latest/core/reflection.html#sqlalchemy.engine.reflection.Inspector.get_columns  # noqa: E501
    insp = inspect(engine)
    for d in insp.get_columns(tablename):
        yield SqlaColumnInspectionInfo(d)


def get_column_info(
    engine: Engine, tablename: str, columnname: str
) -> Optional[SqlaColumnInspectionInfo]:
    """
    For the specified column in the specified table, get column information
    as a :class:`SqlaColumnInspectionInfo` object (or ``None`` if such a
    column can't be found).
    """
    for info in gen_columns_info(engine, tablename):
        if info.name == columnname:
            return info
    return None


def get_column_type(
    engine: Engine, tablename: str, columnname: str
) -> Optional[TypeEngine]:
    """
    For the specified column in the specified table, get its type as an
    instance of an SQLAlchemy column type class (or ``None`` if such a column
    can't be found).

    For more on :class:`TypeEngine`, see
    :func:`cardinal_pythonlib.orm_inspect.coltype_as_typeengine`.
    """
    for info in gen_columns_info(engine, tablename):
        if info.name == columnname:
            return info.type
    return None


def get_column_names(engine: Engine, tablename: str) -> List[str]:
    """
    Get all the database column names for the specified table.
    """
    return [info.name for info in gen_columns_info(engine, tablename)]


# =============================================================================
# More introspection
# =============================================================================


def get_pk_colnames(table_: Table) -> List[str]:
    """
    If a table has a PK, this will return its database column name(s);
    otherwise, ``None``.
    """
    pk_names = []  # type: List[str]
    for col in table_.columns:
        if col.primary_key:
            pk_names.append(col.name)
    return pk_names


def get_single_int_pk_colname(table_: Table) -> Optional[str]:
    """
    If a table has a single-field (non-composite) integer PK, this will
    return its database column name; otherwise, None.

    Note that it is legitimate for a database table to have both a composite
    primary key and a separate ``IDENTITY`` (``AUTOINCREMENT``) integer field.
    This function won't find such columns.
    """
    n_pks = 0
    int_pk_names = []
    for col in table_.columns:
        if col.primary_key:
            n_pks += 1
            if is_sqlatype_integer(col.type):
                int_pk_names.append(col.name)
    if n_pks == 1 and len(int_pk_names) == 1:
        return int_pk_names[0]
    return None


def is_int_autoincrement_column(c: Column, t: Table) -> bool:
    """
    Is this an integer AUTOINCREMENT column? Used by
    get_single_int_autoincrement_colname(); q.v.
    """
    # https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.Column.params.autoincrement  # noqa: E501
    # "The setting only has an effect for columns which are:
    # - Integer derived (i.e. INT, SMALLINT, BIGINT).
    # - Part of the primary key
    # - Not referring to another column via ForeignKey, unless the value is
    #   specified as 'ignore_fk':"
    if not c.primary_key or not is_sqlatype_integer(c.type):
        return False
    a = c.autoincrement
    if isinstance(a, bool):
        # Specified as True or False.
        return a
    if a == "auto":
        # "indicates that a single-column (i.e. non-composite) primary key that
        # is of an INTEGER type with no other client-side or server-side
        # default constructs indicated should receive auto increment semantics
        # automatically." Therefore:
        n_pk = sum(x.primary_key for x in t.columns)
        return n_pk == 1 and c.default is None
    if c.foreign_keys:
        return a == "ignore_fk"
    return False


def get_single_int_autoincrement_colname(table_: Table) -> Optional[str]:
    """
    If a table has a single integer ``AUTOINCREMENT`` column, this will
    return its name; otherwise, ``None``.

    - It's unlikely that a database has >1 ``AUTOINCREMENT`` field anyway, but
      we should check.
    - SQL Server's ``IDENTITY`` keyword is equivalent to MySQL's
      ``AUTOINCREMENT``.
    - Verify against SQL Server:

      .. code-block:: sql

        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE COLUMNPROPERTY(OBJECT_ID(table_schema + '.' + table_name),
                             column_name,
                             'IsIdentity') = 1
        ORDER BY table_name;

      ... https://stackoverflow.com/questions/87747

    - Also:

      .. code-block:: sql

        sp_columns 'tablename';

      ... which is what SQLAlchemy does (``dialects/mssql/base.py``, in
      :func:`get_columns`).
    """
    int_autoinc_names = []  # type: List[str]
    for col in table_.columns:
        if is_int_autoincrement_column(col, table_):
            int_autoinc_names.append(col.name)
    n_autoinc = len(int_autoinc_names)
    if n_autoinc == 1:
        return int_autoinc_names[0]
    if n_autoinc > 1:
        log.warning(
            "Table {!r} has {} integer autoincrement columns",
            table_.name,
            n_autoinc,
        )
    return None


def get_effective_int_pk_col(table_: Table) -> Optional[str]:
    """
    If a table has a single integer primary key, or a single integer
    ``AUTOINCREMENT`` column, return its column name; otherwise, ``None``.
    """
    return (
        get_single_int_pk_colname(table_)
        or get_single_int_autoincrement_colname(table_)
        or None
    )


# =============================================================================
# Execute DDL
# =============================================================================


def execute_ddl(
    engine: Engine, sql: str = None, ddl: DDLElement = None
) -> None:
    """
    Execute DDL, either from a plain SQL string, or from an SQLAlchemy DDL
    element.

    Previously we would use DDL(sql, bind=engine).execute(), but this has gone
    in SQLAlchemy 2.0.

    If you want dialect-conditional execution, create the DDL object with e.g.
    ddl = DDL(sql).execute_if(dialect=SqlaDialectName.SQLSERVER), and pass that
    DDL object to this function.
    """
    assert bool(sql) ^ (ddl is not None)  # one or the other.
    if sql:
        ddl = DDL(sql)
    with engine.connect() as connection:
        # DDL doesn't need a COMMIT.
        connection.execute(ddl)


# =============================================================================
# Indexes
# =============================================================================


def index_exists(
    engine: Engine,
    tablename: str,
    indexname: str = None,
    colnames: Union[str, List[str]] = None,
    raise_if_nonexistent_table: bool = True,
) -> bool:
    """
    Does the specified index exist for the specified table?

    You can specify either the name of the index, or the name(s) of columns.
    But not both.

    If the table doesn't exist, then if raise_if_nonexistent_table is True,
    raise sqlalchemy.exc.NoSuchTableError; otherwise, warn and return False.
    """
    assert bool(indexname) ^ bool(colnames)  # one or the other
    insp = inspect(engine)
    if not raise_if_nonexistent_table and not insp.has_table(tablename):
        log.warning(f"index_exists(): no such table {tablename!r}")
        return False
    indexes = insp.get_indexes(tablename)  # type: List[ReflectedIndex]
    if indexname:
        # Look up by index name.
        return any(i["name"] == indexname for i in indexes)
    else:
        # Look up by column names. All must be present in a given index.
        if isinstance(colnames, str):
            colnames = [colnames]
        return any(
            all(colname in i["column_names"] for colname in colnames)
            for i in indexes
        )


def mssql_get_pk_index_name(
    engine: Engine, tablename: str, schemaname: str = MSSQL_DEFAULT_SCHEMA
) -> str:
    """
    For Microsoft SQL Server specifically: fetch the name of the PK index
    for the specified table (in the specified schema), or ``''`` if none is
    found.
    """
    # http://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.Connection.execute  # noqa: E501
    # http://docs.sqlalchemy.org/en/latest/core/sqlelement.html#sqlalchemy.sql.expression.text  # noqa: E501
    # http://docs.sqlalchemy.org/en/latest/core/sqlelement.html#sqlalchemy.sql.expression.TextClause.bindparams  # noqa: E501
    # http://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.CursorResult  # noqa: E501
    query = text(
        """
SELECT
    kc.name AS index_name
FROM
    sys.key_constraints AS kc
    INNER JOIN sys.tables AS ta ON ta.object_id = kc.parent_object_id
    INNER JOIN sys.schemas AS s ON ta.schema_id = s.schema_id
WHERE
    kc.[type] = 'PK'
    AND ta.name = :tablename
    AND s.name = :schemaname
        """
    ).bindparams(tablename=tablename, schemaname=schemaname)
    with engine.begin() as connection:
        result = connection.execute(query)
        row = result.fetchone()
        return row[0] if row else ""


def mssql_table_has_ft_index(
    engine: Engine, tablename: str, schemaname: str = MSSQL_DEFAULT_SCHEMA
) -> bool:
    """
    For Microsoft SQL Server specifically: does the specified table (in the
    specified schema) have at least one full-text index?
    """
    query = text(
        """
SELECT
    COUNT(*)
FROM
    sys.key_constraints AS kc
    INNER JOIN sys.tables AS ta ON ta.object_id = kc.parent_object_id
    INNER JOIN sys.schemas AS s ON ta.schema_id = s.schema_id
    INNER JOIN sys.fulltext_indexes AS fi ON fi.object_id = ta.object_id
WHERE
    ta.name = :tablename
    AND s.name = :schemaname
        """
    ).bindparams(tablename=tablename, schemaname=schemaname)
    with engine.begin() as connection:
        result = connection.execute(query)
        row = result.fetchone()
        return row[0] > 0


def mssql_transaction_count(engine_or_conn: Union[Connection, Engine]) -> int:
    """
    For Microsoft SQL Server specifically: fetch the value of the ``TRANCOUNT``
    variable (see e.g.
    https://docs.microsoft.com/en-us/sql/t-sql/functions/trancount-transact-sql?view=sql-server-2017).
    Returns ``None`` if it can't be found (unlikely?).
    """
    query = text("SELECT @@TRANCOUNT")
    if isinstance(engine_or_conn, Connection):
        result = engine_or_conn.execute(query)
        row = result.fetchone()
    elif isinstance(engine_or_conn, Engine):
        with engine_or_conn.begin() as connection:
            result = connection.execute(query)
            row = result.fetchone()
    else:
        raise ValueError(f"Unexpected {engine_or_conn=}")
    return row[0] if row else None


def add_index(
    engine: Engine,
    sqla_column: Column = None,
    multiple_sqla_columns: List[Column] = None,
    unique: bool = False,
    fulltext: bool = False,
    length: int = None,
) -> None:
    """
    Adds an index to a database column (or, in restricted circumstances,
    several columns).

    The table name is worked out from the :class:`Column` object.

    DIALECT-AWARE.

    Args:
        engine: SQLAlchemy :class:`Engine` object
        sqla_column: single column to index
        multiple_sqla_columns: multiple columns to index (see below)
        unique: make a ``UNIQUE`` index?
        fulltext: make a ``FULLTEXT`` index?
        length: index length to use (default ``None``)

    Restrictions:

    - Specify either ``sqla_column`` or ``multiple_sqla_columns``, not both.
    - The normal method is ``sqla_column``.
    - ``multiple_sqla_columns`` is only used for Microsoft SQL Server full-text
      indexing (as this database permits only one full-text index per table,
      though that index can be on multiple columns).

    """
    # We used to process a table as a unit; this makes index creation faster
    # (using ALTER TABLE).
    # http://dev.mysql.com/doc/innodb/1.1/en/innodb-create-index-examples.html  # noqa: E501
    # ... ignored in transition to SQLAlchemy

    def quote(identifier: str) -> str:
        return quote_identifier(identifier, engine)

    is_mssql = engine.dialect.name == SqlaDialectName.MSSQL
    is_mysql = engine.dialect.name == SqlaDialectName.MYSQL
    is_sqlite = engine.dialect.name == SqlaDialectName.SQLITE

    multiple_sqla_columns = multiple_sqla_columns or []  # type: List[Column]
    if multiple_sqla_columns and not (fulltext and is_mssql):
        raise ValueError(
            "add_index: Use multiple_sqla_columns only for mssql "
            "(Microsoft SQL Server) full-text indexing"
        )
    if bool(multiple_sqla_columns) == (sqla_column is not None):
        raise ValueError(
            f"add_index: Use either sqla_column or multiple_sqla_columns, "
            f"not both (sqla_column = {sqla_column!r}, "
            f"multiple_sqla_columns = {multiple_sqla_columns!r})"
        )
    if sqla_column is not None:
        colnames = [sqla_column.name]
        sqla_table = sqla_column.table
        tablename = sqla_table.name
    else:
        colnames = [c.name for c in multiple_sqla_columns]
        sqla_table = multiple_sqla_columns[0].table
        tablename = sqla_table.name
        if any(c.table.name != tablename for c in multiple_sqla_columns[1:]):
            raise ValueError(
                f"add_index: tablenames are inconsistent in "
                f"multiple_sqla_columns = {multiple_sqla_columns!r}"
            )

    if fulltext:
        if is_mssql:
            idxname = ""  # they are unnamed
        else:
            idxname = "_idxft_{}".format("_".join(colnames))
    else:
        idxname = "_idx_{}".format("_".join(colnames))
    if is_sqlite:
        # SQLite doesn't allow indexes with the same names on different tables.
        idxname = f"{tablename}_{idxname}"
    if idxname and index_exists(engine, tablename, idxname):
        log.info(
            f"Skipping creation of index {idxname} on "
            f"table {tablename}; already exists"
        )
        return
        # because it will crash if you add it again!
    log.info(
        "Creating{ft} index {i} on table {t}, column(s) {c}",
        ft=" full-text" if fulltext else "",
        i=idxname or "<unnamed>",
        t=tablename,
        c=", ".join(colnames),
    )

    if fulltext:
        if is_mysql:
            log.info(
                "OK to ignore this warning, if it follows next: "
                '"InnoDB rebuilding table to add column FTS_DOC_ID"'
            )
            # https://dev.mysql.com/doc/refman/5.6/en/innodb-fulltext-index.html
            sql = (
                "ALTER TABLE {tablename} "
                "ADD FULLTEXT INDEX {idxname} ({colnames})".format(
                    tablename=quote(tablename),
                    idxname=quote(idxname),
                    colnames=", ".join(quote(c) for c in colnames),
                )
            )
            execute_ddl(engine, sql=sql)

        elif is_mssql:  # Microsoft SQL Server
            # https://msdn.microsoft.com/library/ms187317(SQL.130).aspx
            # Argh! Complex.
            # Note that the database must also have had a
            #   CREATE FULLTEXT CATALOG somename AS DEFAULT;
            # statement executed on it beforehand.
            connection = Connection(engine)
            schemaname = (
                connection.schema_for_object(sqla_table)
                or MSSQL_DEFAULT_SCHEMA
            )
            if mssql_table_has_ft_index(
                engine=engine, tablename=tablename, schemaname=schemaname
            ):
                log.info(
                    f"... skipping creation of full-text index on table "
                    f"{tablename}; a full-text index already exists for that "
                    f"table; you can have only one full-text index per table, "
                    f"though it can be on multiple columns"
                )
                return
            pk_index_name = mssql_get_pk_index_name(
                engine=engine, tablename=tablename, schemaname=schemaname
            )
            if not pk_index_name:
                raise ValueError(
                    f"To make a FULLTEXT index under SQL Server, we need to "
                    f"know the name of the PK index, but couldn't find one "
                    f"via mssql_get_pk_index_name() for table {tablename!r}"
                )
            # We don't name the FULLTEXT index itself, but it has to relate
            # to an existing unique index.
            sql = (
                "CREATE FULLTEXT INDEX ON {tablename} ({colnames}) "
                "KEY INDEX {keyidxname} ".format(
                    tablename=quote(tablename),
                    keyidxname=quote(pk_index_name),
                    colnames=", ".join(quote(c) for c in colnames),
                )
            )
            # SQL Server won't let you do this inside a transaction:
            # "CREATE FULLTEXT INDEX statement cannot be used inside a user
            # transaction."
            # https://msdn.microsoft.com/nl-nl/library/ms191544(v=sql.105).aspx
            # So let's ensure any preceding transactions are completed, and
            # run the SQL in a raw way:
            # engine.execute(sql).execution_options(autocommit=False)
            # http://docs.sqlalchemy.org/en/latest/core/connections.html#understanding-autocommit
            #
            # ... lots of faff with this (see test code in no_transactions.py)
            # ... ended up using explicit "autocommit=True" parameter (for
            #     pyodbc); see create_indexes()
            transaction_count = mssql_transaction_count(engine)
            if transaction_count != 0:
                log.critical(
                    f"SQL Server transaction count (should be 0): "
                    f"{transaction_count}"
                )
                # Executing serial COMMITs or a ROLLBACK won't help here if
                # this transaction is due to Python DBAPI default behaviour.
            execute_ddl(engine, sql=sql)

            # The reversal procedure is DROP FULLTEXT INDEX ON tablename;

        else:
            log.error(
                f"Don't know how to make full text index on dialect "
                f"{engine.dialect.name}"
            )

    else:
        index = Index(idxname, sqla_column, unique=unique, mysql_length=length)
        index.create(engine)
        # Index creation doesn't require a commit.


# =============================================================================
# More DDL
# =============================================================================

# https://stackoverflow.com/questions/18835740/does-bigint-auto-increment-work-for-sqlalchemy-with-sqlite  # noqa: E501

BigIntegerForAutoincrementType = BigInteger()
BigIntegerForAutoincrementType = BigIntegerForAutoincrementType.with_variant(
    postgresql.BIGINT(), SqlaDialectName.POSTGRES
)
BigIntegerForAutoincrementType = BigIntegerForAutoincrementType.with_variant(
    mssql.BIGINT(), SqlaDialectName.MSSQL
)
BigIntegerForAutoincrementType = BigIntegerForAutoincrementType.with_variant(
    mysql.BIGINT(), SqlaDialectName.MYSQL
)
BigIntegerForAutoincrementType = BigIntegerForAutoincrementType.with_variant(
    sqlite.INTEGER(), SqlaDialectName.SQLITE
)


def make_bigint_autoincrement_column(
    column_name: str, nullable: bool = False, comment: str = None
) -> Column:
    """
    Returns an instance of :class:`Column` representing a :class:`BigInteger`
    ``AUTOINCREMENT`` column, or the closest that the database engine can
    manage.
    """
    return Column(
        column_name,
        BigIntegerForAutoincrementType,
        Identity(start=1, increment=1),
        # https://docs.sqlalchemy.org/en/20/core/defaults.html#identity-ddl
        autoincrement=True,
        nullable=nullable,
        comment=comment,
    )
    # see also: https://stackoverflow.com/questions/2937229


def column_creation_ddl(sqla_column: Column, dialect: Dialect) -> str:
    """
    Returns DDL to create a column, using the specified dialect.

    The column should already be bound to a table (because e.g. the SQL Server
    dialect requires this for DDL generation). If you don't append the column
    to a Table object, the DDL generation step gives
    "sqlalchemy.exc.CompileError: mssql requires Table-bound columns in order
    to generate DDL".

    Testing: see schema_tests.py
    """
    return str(CreateColumn(sqla_column).compile(dialect=dialect))


# noinspection PyUnresolvedReferences
def giant_text_sqltype(dialect: Dialect) -> str:
    """
    Returns the SQL column type used to make very large text columns for a
    given dialect.

    DIALECT-AWARE.

    Args:
        dialect: a SQLAlchemy :class:`Dialect`
    Returns:
        the SQL data type of "giant text", typically 'LONGTEXT' for MySQL
        and 'NVARCHAR(MAX)' for SQL Server.
    """
    dname = dialect.name
    if dname == SqlaDialectName.MSSQL:
        return "NVARCHAR(MAX)"
        # https://learn.microsoft.com/en-us/sql/t-sql/data-types/nchar-and-nvarchar-transact-sql?view=sql-server-ver16  # noqa: E501
    elif dname == SqlaDialectName.MYSQL:
        return "LONGTEXT"
        # https://dev.mysql.com/doc/refman/8.4/en/blob.html
    elif dname == SqlaDialectName.ORACLE:
        return "LONG"
        # https://docs.oracle.com/cd/A58617_01/server.804/a58241/ch5.htm
    elif dname == SqlaDialectName.POSTGRES:
        return "TEXT"
        # https://www.postgresql.org/docs/current/datatype-character.html
    elif dname == SqlaDialectName.SQLITE:
        return "TEXT"
        # https://www.sqlite.org/datatype3.html
    elif dname == SqlaDialectName.DATABRICKS:
        return "STRING"
        # https://github.com/databricks/databricks-sqlalchemy
    else:
        raise ValueError(f"Unknown dialect: {dname}")


# =============================================================================
# SQLAlchemy column types
# =============================================================================

# -----------------------------------------------------------------------------
# Reverse a textual SQL column type to an SQLAlchemy column type
# -----------------------------------------------------------------------------

RE_MYSQL_ENUM_COLTYPE = re.compile(r"ENUM\((?P<valuelist>.+)\)")
RE_COLTYPE_WITH_COLLATE = re.compile(r"(?P<maintype>.+) COLLATE .+")
RE_COLTYPE_WITH_ONE_PARAM = re.compile(r"(?P<type>\w+)\((?P<size>\w+)\)")
# ... e.g. "VARCHAR(10)"
RE_COLTYPE_WITH_TWO_PARAMS = re.compile(
    r"(?P<type>\w+)\((?P<size>\w+),\s*(?P<dp>\w+)\)"
)
# ... e.g. "DECIMAL(10, 2)"


# http://www.w3schools.com/sql/sql_create_table.asp


def _get_sqla_coltype_class_from_str(
    coltype: str, dialect: Dialect
) -> Type[TypeEngine]:
    """
    Returns the SQLAlchemy class corresponding to a particular SQL column
    type in a given dialect.

    DIALECT-AWARE.

    Performs an upper- and lower-case search.
    For example, the SQLite dialect uses upper case, and the
    MySQL dialect uses lower case.

    For exploratory thinking, see
    dev_notes/convert_sql_string_coltype_to_sqlalchemy_type.py.

    DISCUSSION AT: https://github.com/sqlalchemy/sqlalchemy/discussions/12230
    """
    if hasattr(dialect, "ischema_names"):
        # The built-in dialects all have this, even though it's an internal
        # detail.
        ischema_names = dialect.ischema_names
        try:
            return ischema_names[coltype.upper()]
        except KeyError:
            return ischema_names[coltype.lower()]
    elif dialect.name == SqlaDialectName.DATABRICKS:
        # Ugly hack.
        # Databricks is an example that doesn't have ischema_names.
        try:
            return DATABRICKS_SQLCOLTYPE_TO_SQLALCHEMY_GENERIC[coltype.upper()]
        except KeyError:
            raise ValueError(
                f"Don't know how to convert SQL column type {coltype!r} "
                f"to SQLAlchemy dialect {dialect!r}"
            )
    else:
        raise ValueError(
            f"Don't know a generic way to convert SQL column types "
            f"(in text format) to SQLAlchemy dialect {dialect.name!r}. "
        )


def get_list_of_sql_string_literals_from_quoted_csv(x: str) -> List[str]:
    """
    Used to extract SQL column type parameters. For example, MySQL has column
    types that look like ``ENUM('a', 'b', 'c', 'd')``. This function takes the
    ``"'a', 'b', 'c', 'd'"`` and converts it to ``['a', 'b', 'c', 'd']``.
    """
    f = io.StringIO(x)
    reader = csv.reader(
        f,
        delimiter=",",
        quotechar="'",
        quoting=csv.QUOTE_ALL,
        skipinitialspace=True,
    )
    for line in reader:  # should only be one
        return [x for x in line]


@lru_cache(maxsize=None)
def get_sqla_coltype_from_dialect_str(
    coltype: str, dialect: Dialect
) -> TypeEngine:
    """
    Returns an SQLAlchemy column type, given a column type name (a string) and
    an SQLAlchemy dialect. For example, this might convert the string
    ``INTEGER(11)`` to an SQLAlchemy ``Integer(length=11)``.

    NOTE that the reverse operation is performed by ``str(coltype)`` or
    ``coltype.compile()`` or ``coltype.compile(dialect)``; see
    :class:`TypeEngine`.

    DIALECT-AWARE.

    Args:
        dialect: a SQLAlchemy :class:`Dialect` class

        coltype: a ``str()`` representation, e.g. from ``str(c['type'])`` where
            ``c`` is an instance of :class:`sqlalchemy.sql.schema.Column`.

    Returns:
        a Python object that is a subclass of
        :class:`sqlalchemy.types.TypeEngine`

    Example:

    .. code-block:: python

        get_sqla_coltype_from_string('INTEGER(11)', engine.dialect)
        # gives: Integer(length=11)

    Notes:

    - :class:`sqlalchemy.engine.default.DefaultDialect` is the dialect base
      class

    - a dialect contains these things of interest:

      - ``ischema_names``: string-to-class dictionary
      - ``type_compiler``: instance of e.g.
        :class:`sqlalchemy.sql.compiler.GenericTypeCompiler`. This has a
        ``process()`` method, but that operates on :class:`TypeEngine` objects.
      - ``get_columns``: takes a table name, inspects the database

    - example of the dangers of ``eval``:
      https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html

    - An example of a function doing the reflection/inspection within
      SQLAlchemy is
      :func:`sqlalchemy.dialects.mssql.base.MSDialect.get_columns`,
      which has this lookup: ``coltype = self.ischema_names.get(type, None)``

    Caveats:

    - the parameters, e.g. ``DATETIME(6)``, do NOT necessarily either work at
      all or work correctly. For example, SQLAlchemy will happily spit out
      ``'INTEGER(11)'`` but its :class:`sqlalchemy.sql.sqltypes.INTEGER` class
      takes no parameters, so you get the error ``TypeError: object() takes no
      parameters``. Similarly, MySQL's ``DATETIME(6)`` uses the 6 to refer to
      precision, but the ``DATETIME`` class in SQLAlchemy takes only a boolean
      parameter (timezone).
    - However, sometimes we have to have parameters, e.g. ``VARCHAR`` length.
    - Thus, this is a bit useless.
    - Fixed, with a few special cases.
    """
    size = None  # type: Optional[int]
    dp = None  # type: Optional[int]
    args = []  # type: List[Any]
    kwargs = {}  # type: Dict[str, Any]
    basetype = ""

    # noinspection PyPep8,PyBroadException
    try:
        # Split e.g. "VARCHAR(32) COLLATE blah" into "VARCHAR(32)", "who cares"
        m = RE_COLTYPE_WITH_COLLATE.match(coltype)
        if m is not None:
            coltype = m.group("maintype")

        found = False

        if not found:
            # Deal with ENUM('a', 'b', 'c', ...)
            m = RE_MYSQL_ENUM_COLTYPE.match(coltype)
            if m is not None:
                # Convert to VARCHAR with max size being that of largest enum
                basetype = "VARCHAR"
                values = get_list_of_sql_string_literals_from_quoted_csv(
                    m.group("valuelist")
                )
                length = max(len(x) for x in values)
                kwargs = {"length": length}
                found = True

        if not found:
            # Split e.g. "DECIMAL(10, 2)" into DECIMAL, 10, 2
            m = RE_COLTYPE_WITH_TWO_PARAMS.match(coltype)
            if m is not None:
                basetype = m.group("type").upper()
                size = ast.literal_eval(m.group("size"))
                dp = ast.literal_eval(m.group("dp"))
                found = True

        if not found:
            # Split e.g. "VARCHAR(32)" into VARCHAR, 32
            m = RE_COLTYPE_WITH_ONE_PARAM.match(coltype)
            if m is not None:
                basetype = m.group("type").upper()
                size_text = m.group("size").strip().upper()
                if size_text != "MAX":
                    size = ast.literal_eval(size_text)
                found = True

        if not found:
            basetype = coltype.upper()

        # Special cases: pre-processing
        # noinspection PyUnresolvedReferences
        if (
            dialect.name == SqlaDialectName.MSSQL
            and basetype.lower() == "integer"
        ):
            basetype = "int"

        cls = _get_sqla_coltype_class_from_str(basetype, dialect)

        # Special cases: post-processing
        if basetype == "DATETIME" and size:
            # First argument to DATETIME() is timezone, so...
            # noinspection PyUnresolvedReferences
            if dialect.name == SqlaDialectName.MYSQL:
                kwargs = {"fsp": size}
            else:
                pass
        else:
            args = [x for x in (size, dp) if x is not None]

        try:
            return cls(*args, **kwargs)
        except TypeError:
            return cls()

    except Exception:
        # noinspection PyUnresolvedReferences
        raise ValueError(
            f"Failed to convert SQL type {coltype!r} in dialect "
            f"{dialect.name!r} to an SQLAlchemy type"
        )


# get_sqla_coltype_from_dialect_str("INTEGER", engine.dialect)
# get_sqla_coltype_from_dialect_str("INTEGER(11)", engine.dialect)
# get_sqla_coltype_from_dialect_str("VARCHAR(50)", engine.dialect)
# get_sqla_coltype_from_dialect_str("DATETIME", engine.dialect)
# get_sqla_coltype_from_dialect_str("DATETIME(6)", engine.dialect)


# =============================================================================
# Do special dialect conversions on SQLAlchemy SQL types (of class type)
# =============================================================================


def remove_collation(coltype: TypeEngine) -> TypeEngine:
    """
    Returns a copy of the specific column type with any ``COLLATION`` removed.
    """
    if not getattr(coltype, "collation", None):
        return coltype
    newcoltype = copy.copy(coltype)
    newcoltype.collation = None
    return newcoltype


@lru_cache(maxsize=None)
def convert_sqla_type_for_dialect(
    coltype: TypeEngine,
    dialect: Dialect,
    strip_collation: bool = True,
    convert_mssql_timestamp: bool = True,
    expand_for_scrubbing: bool = False,
) -> TypeEngine:
    """
    Converts an SQLAlchemy column type from one SQL dialect to another.

    DIALECT-AWARE.

    Args:
        coltype: SQLAlchemy column type in the source dialect

        dialect: destination :class:`Dialect`

        strip_collation: remove any ``COLLATION`` information?

        convert_mssql_timestamp:
            since you cannot write to a SQL Server ``TIMESTAMP`` field, setting
            this option to ``True`` (the default) converts such types to
            something equivalent but writable.

        expand_for_scrubbing:
            The purpose of expand_for_scrubbing is that, for example, a
            ``VARCHAR(200)`` field containing one or more instances of
            ``Jones``, where ``Jones`` is to be replaced with ``[XXXXXX]``,
            will get longer (by an unpredictable amount). So, better to expand
            to unlimited length.

    Returns:
        an SQLAlchemy column type instance, in the destination dialect

    """
    assert coltype is not None

    to_mysql = dialect.name == SqlaDialectName.MYSQL
    to_mssql = dialect.name == SqlaDialectName.MSSQL
    typeclass = type(coltype)

    # -------------------------------------------------------------------------
    # Text
    # -------------------------------------------------------------------------
    if isinstance(coltype, sqltypes.Enum):
        return sqltypes.String(length=coltype.length)
    if isinstance(coltype, sqltypes.UnicodeText):
        # Unbounded Unicode text.
        # Includes derived classes such as mssql.base.NTEXT.
        return sqltypes.UnicodeText()
    if isinstance(coltype, sqltypes.Text):
        # Unbounded text, more generally. (UnicodeText inherits from Text.)
        # Includes sqltypes.TEXT.
        return sqltypes.Text()
    # Everything inheriting from String has a length property, but can be None.
    # There are types that can be unlimited in SQL Server, e.g. VARCHAR(MAX)
    # and NVARCHAR(MAX), that MySQL needs a length for. (Failure to convert
    # gives e.g.: 'NVARCHAR requires a length on dialect mysql'.)
    if isinstance(coltype, sqltypes.Unicode):
        # Includes NVARCHAR(MAX) in SQL -> NVARCHAR() in SQLAlchemy.
        if (coltype.length is None and to_mysql) or expand_for_scrubbing:
            return sqltypes.UnicodeText()
    # The most general case; will pick up any other string types.
    if isinstance(coltype, sqltypes.String):
        # Includes VARCHAR(MAX) in SQL -> VARCHAR() in SQLAlchemy
        if (coltype.length is None and to_mysql) or expand_for_scrubbing:
            return sqltypes.Text()
        if strip_collation:
            return remove_collation(coltype)
        return coltype

    # -------------------------------------------------------------------------
    # Binary
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # BIT
    # -------------------------------------------------------------------------
    if typeclass == mssql.base.BIT and to_mysql:
        # MySQL BIT objects have a length attribute.
        return mysql.base.BIT()

    # -------------------------------------------------------------------------
    # TIMESTAMP
    # -------------------------------------------------------------------------
    is_mssql_timestamp = isinstance(coltype, MSSQL_TIMESTAMP)
    if is_mssql_timestamp and to_mssql and convert_mssql_timestamp:
        # You cannot write explicitly to a TIMESTAMP field in SQL Server; it's
        # used for autogenerated values only.
        # - https://stackoverflow.com/questions/10262426/sql-server-cannot-insert-an-explicit-value-into-a-timestamp-column  # noqa: E501
        # - https://social.msdn.microsoft.com/Forums/sqlserver/en-US/5167204b-ef32-4662-8e01-00c9f0f362c2/how-to-tranfer-a-column-with-timestamp-datatype?forum=transactsql  # noqa: E501
        #   ... suggesting BINARY(8) to store the value.
        # MySQL is more helpful:
        # - https://stackoverflow.com/questions/409286/should-i-use-field-datetime-or-timestamp  # noqa: E501
        return mssql.base.BINARY(8)

    # -------------------------------------------------------------------------
    # Some other type
    # -------------------------------------------------------------------------
    return coltype


# =============================================================================
# Questions about SQLAlchemy column types
# =============================================================================


def is_sqlatype_binary(coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type a binary type?
    """
    # Several binary types inherit internally from _Binary, making that the
    # easiest to check.
    coltype = coltype_as_typeengine(coltype)
    # noinspection PyProtectedMember
    return isinstance(coltype, sqltypes._Binary)


def is_sqlatype_date(coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type a date type?
    """
    coltype = coltype_as_typeengine(coltype)
    return isinstance(coltype, sqltypes.DateTime) or isinstance(
        coltype, sqltypes.Date
    )


def is_sqlatype_integer(coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type an integer type?
    """
    coltype = coltype_as_typeengine(coltype)
    return isinstance(coltype, sqltypes.Integer)


def is_sqlatype_numeric(coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type one that inherits from :class:`Numeric`,
    such as :class:`Float`, :class:`Decimal`?

    Note that integers don't count as Numeric!
    """
    coltype = coltype_as_typeengine(coltype)
    return isinstance(coltype, sqltypes.Numeric)  # includes Float, Decimal


def is_sqlatype_string(coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type a string type?
    """
    coltype = coltype_as_typeengine(coltype)
    return isinstance(coltype, sqltypes.String)


def is_sqlatype_text_of_length_at_least(
    coltype: Union[TypeEngine, VisitableType],
    min_length: int = MIN_TEXT_LENGTH_FOR_FREETEXT_INDEX,
) -> bool:
    """
    Is the SQLAlchemy column type a string type that's at least the specified
    length?
    """
    coltype = coltype_as_typeengine(coltype)
    if not isinstance(coltype, sqltypes.String):
        return False  # not a string/text type at all
    if coltype.length is None:
        return True  # string of unlimited length
    return coltype.length >= min_length


def is_sqlatype_text_over_one_char(
    coltype: Union[TypeEngine, VisitableType]
) -> bool:
    """
    Is the SQLAlchemy column type a string type that's more than one character
    long?
    """
    return is_sqlatype_text_of_length_at_least(coltype, 2)


def does_sqlatype_merit_fulltext_index(
    coltype: Union[TypeEngine, VisitableType],
    min_length: int = MIN_TEXT_LENGTH_FOR_FREETEXT_INDEX,
) -> bool:
    """
    Is the SQLAlchemy column type a type that might merit a ``FULLTEXT``
    index (meaning a string type of at least ``min_length``)?
    """
    return is_sqlatype_text_of_length_at_least(coltype, min_length)


def does_sqlatype_require_index_len(
    coltype: Union[TypeEngine, VisitableType]
) -> bool:
    """
    Is the SQLAlchemy column type one that requires its indexes to have a
    length specified?

    (MySQL, at least, requires index length to be specified for ``BLOB`` and
    ``TEXT`` columns:
    https://dev.mysql.com/doc/refman/5.7/en/create-index.html.)
    """
    coltype = coltype_as_typeengine(coltype)
    if isinstance(coltype, sqltypes.Text):
        return True
    if isinstance(coltype, sqltypes.LargeBinary):
        return True
    return False


# =============================================================================
# hack_in_mssql_xml_type
# =============================================================================
#
# Removed, as mssql.base.ischema_names["xml"] is now defined.


# =============================================================================
# Check column definition equality
# =============================================================================


def column_types_equal(a_coltype: TypeEngine, b_coltype: TypeEngine) -> bool:
    """
    Checks that two SQLAlchemy column types are equal (by comparing ``str()``
    versions of them).

    See https://stackoverflow.com/questions/34787794/sqlalchemy-column-type-comparison.

    IMPERFECT.
    """  # noqa: E501
    return str(a_coltype) == str(b_coltype)


def columns_equal(a: Column, b: Column) -> bool:
    """
    Are two SQLAlchemy columns are equal? Checks based on:

    - column ``name``
    - column ``type`` (see :func:`column_types_equal`)
    - ``nullable``
    """
    return (
        a.name == b.name
        and column_types_equal(a.type, b.type)
        and a.nullable == b.nullable
    )


def column_lists_equal(a: List[Column], b: List[Column]) -> bool:
    """
    Are all columns in list ``a`` equal to their counterparts in list ``b``,
    as per :func:`columns_equal`?
    """
    n = len(a)
    if len(b) != n:
        return False
    for i in range(n):
        if not columns_equal(a[i], b[i]):
            log.debug("Mismatch: {!r} != {!r}", a[i], b[i])
            return False
    return True


def indexes_equal(a: Index, b: Index) -> bool:
    """
    Are two indexes equal? Checks by comparing ``str()`` versions of them.
    (AM UNSURE IF THIS IS ENOUGH.)
    """
    return str(a) == str(b)


def index_lists_equal(a: List[Index], b: List[Index]) -> bool:
    """
    Are all indexes in list ``a`` equal to their counterparts in list ``b``,
    as per :func:`indexes_equal`?
    """
    n = len(a)
    if len(b) != n:
        return False
    for i in range(n):
        if not indexes_equal(a[i], b[i]):
            log.debug("Mismatch: {!r} != {!r}", a[i], b[i])
            return False
    return True
