#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/schema.py

"""
===============================================================================

    Original code copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Functions to work with SQLAlchemy schemas (schemata) directly, via SQLAlchemy
Core.**

"""

import ast
import contextlib
import copy
import csv
from functools import lru_cache
import io
import logging
import re
from typing import Any, Dict, Generator, List, Optional, Type, Union

from sqlalchemy.dialects import mssql, mysql
# noinspection PyProtectedMember
from sqlalchemy.engine import Connection, Engine, ResultProxy
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.schema import (Column, CreateColumn, DDL, MetaData, Index,
                               Sequence, Table)
from sqlalchemy.sql import sqltypes, text
from sqlalchemy.sql.sqltypes import BigInteger, TypeEngine
from sqlalchemy.sql.visitors import VisitableType

from cardinal_pythonlib.sqlalchemy.dialect import (
    quote_identifier,
    SqlaDialectName,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# =============================================================================
# Constants
# =============================================================================

MSSQL_DEFAULT_SCHEMA = 'dbo'
POSTGRES_DEFAULT_SCHEMA = 'public'


# =============================================================================
# Inspect tables (SQLAlchemy Core)
# =============================================================================

def get_table_names(engine: Engine) -> List[str]:
    """
    Returns a list of database table names from the :class:`Engine`.
    """
    insp = Inspector.from_engine(engine)
    return insp.get_table_names()


def get_view_names(engine: Engine) -> List[str]:
    """
    Returns a list of database view names from the :class:`Engine`.
    """
    insp = Inspector.from_engine(engine)
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

    A clearer way of getting information than the plain ``dict`` that SQLAlchemy
    uses.
    """
    def __init__(self, sqla_info_dict: Dict[str, Any]) -> None:
        """
        Args:
            sqla_info_dict:
                see
        
                - http://docs.sqlalchemy.org/en/latest/core/reflection.html#sqlalchemy.engine.reflection.Inspector.get_columns
                - https://bitbucket.org/zzzeek/sqlalchemy/issues/4051/sqlalchemyenginereflectioninspectorget_col
        """  # noqa
        # log.debug(repr(sqla_info_dict))
        self.name = sqla_info_dict['name']  # type: str
        self.type = sqla_info_dict['type']  # type: TypeEngine
        self.nullable = sqla_info_dict['nullable']  # type: bool
        self.default = sqla_info_dict['default']  # type: str  # SQL string expression  # noqa
        self.attrs = sqla_info_dict.get('attrs', {})  # type: Dict[str, Any]
        self.comment = sqla_info_dict.get('comment', '')
        # ... NB not appearing in


def gen_columns_info(engine: Engine,
                     tablename: str) -> Generator[SqlaColumnInspectionInfo,
                                                  None, None]:
    """
    For the specified table, generate column information as
    :class:`SqlaColumnInspectionInfo` objects.
    """
    # Dictionary structure: see
    # http://docs.sqlalchemy.org/en/latest/core/reflection.html#sqlalchemy.engine.reflection.Inspector.get_columns  # noqa
    insp = Inspector.from_engine(engine)
    for d in insp.get_columns(tablename):
        yield SqlaColumnInspectionInfo(d)


def get_column_info(engine: Engine, tablename: str,
                    columnname: str) -> Optional[SqlaColumnInspectionInfo]:
    """
    For the specified column in the specified table, get column information
    as a :class:`SqlaColumnInspectionInfo` object (or ``None`` if such a
    column can't be found).
    """
    for info in gen_columns_info(engine, tablename):
        if info.name == columnname:
            return info
    return None


def get_column_type(engine: Engine, tablename: str,
                    columnname: str) -> Optional[TypeEngine]:
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

      ... http://stackoverflow.com/questions/87747

    - Also:

      .. code-block:: sql

        sp_columns 'tablename';

      ... which is what SQLAlchemy does (``dialects/mssql/base.py``, in
      :func:`get_columns`).
    """
    n_autoinc = 0
    int_autoinc_names = []
    for col in table_.columns:
        if col.autoincrement:
            n_autoinc += 1
            if is_sqlatype_integer(col.type):
                int_autoinc_names.append(col.name)
    if n_autoinc > 1:
        log.warning("Table {} has {} autoincrement columns".format(
            repr(table_.name), n_autoinc))
    if n_autoinc == 1 and len(int_autoinc_names) == 1:
        return int_autoinc_names[0]
    return None


def get_effective_int_pk_col(table_: Table) -> Optional[str]:
    """
    If a table has a single integer primary key, or a single integer
    ``AUTOINCREMENT`` column, return its column name; otherwise, ``None``.
    """
    return (
        get_single_int_pk_colname(table_) or
        get_single_int_autoincrement_colname(table_) or
        None
    )


# =============================================================================
# Indexes
# =============================================================================

def index_exists(engine: Engine, tablename: str, indexname: str) -> bool:
    """
    Does the specified index exist for the specified table?
    """
    insp = Inspector.from_engine(engine)
    return any(i['name'] == indexname for i in insp.get_indexes(tablename))


def mssql_get_pk_index_name(engine: Engine,
                            tablename: str,
                            schemaname: str = MSSQL_DEFAULT_SCHEMA) -> str:
    """
    For Microsoft SQL Server specifically: fetch the name of the PK index
    for the specified table (in the specified schema), or ``''`` if none is
    found.
    """
    # http://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.Connection.execute  # noqa
    # http://docs.sqlalchemy.org/en/latest/core/sqlelement.html#sqlalchemy.sql.expression.text  # noqa
    # http://docs.sqlalchemy.org/en/latest/core/sqlelement.html#sqlalchemy.sql.expression.TextClause.bindparams  # noqa
    # http://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.ResultProxy  # noqa
    query = text("""
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
    """).bindparams(
        tablename=tablename,
        schemaname=schemaname,
    )
    with contextlib.closing(
            engine.execute(query)) as result:  # type: ResultProxy  # noqa
        row = result.fetchone()
        return row[0] if row else ''


def mssql_table_has_ft_index(engine: Engine,
                             tablename: str,
                             schemaname: str = MSSQL_DEFAULT_SCHEMA) -> bool:
    """
    For Microsoft SQL Server specifically: does the specified table (in the
    specified schema) have at least one full-text index?
    """
    query = text("""
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
    """).bindparams(
        tablename=tablename,
        schemaname=schemaname,
    )
    with contextlib.closing(
            engine.execute(query)) as result:  # type: ResultProxy  # noqa
        row = result.fetchone()
        return row[0] > 0


def mssql_transaction_count(engine_or_conn: Union[Connection, Engine]) -> int:
    """
    For Microsoft SQL Server specifically: fetch the value of the ``TRANCOUNT``
    variable (see e.g.
    https://docs.microsoft.com/en-us/sql/t-sql/functions/trancount-transact-sql?view=sql-server-2017).
    Returns ``None`` if it can't be found (unlikely?).
    """
    sql = "SELECT @@TRANCOUNT"
    with contextlib.closing(
            engine_or_conn.execute(sql)) as result:  # type: ResultProxy  # noqa
        row = result.fetchone()
        return row[0] if row else None


def add_index(engine: Engine,
              sqla_column: Column = None,
              multiple_sqla_columns: List[Column] = None,
              unique: bool = False,
              fulltext: bool = False,
              length: int = None) -> None:
    """
    Adds an index to a database column (or, in restricted circumstances,
    several columns).

    The table name is worked out from the :class:`Column` object.

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
    # http://dev.mysql.com/doc/innodb/1.1/en/innodb-create-index-examples.html  # noqa
    # ... ignored in transition to SQLAlchemy

    def quote(identifier: str) -> str:
        return quote_identifier(identifier, engine)

    is_mssql = engine.dialect.name == SqlaDialectName.MSSQL
    is_mysql = engine.dialect.name == SqlaDialectName.MYSQL

    multiple_sqla_columns = multiple_sqla_columns or []  # type: List[Column]
    if multiple_sqla_columns and not (fulltext and is_mssql):
        raise ValueError("add_index: Use multiple_sqla_columns only for mssql "
                         "(Microsoft SQL Server) full-text indexing")
    if bool(multiple_sqla_columns) == (sqla_column is not None):
        raise ValueError(
            "add_index: Use either sqla_column or multiple_sqla_columns, not "
            "both (sqla_column = {}, multiple_sqla_columns = {}".format(
                repr(sqla_column), repr(multiple_sqla_columns)))
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
                "add_index: tablenames are inconsistent in "
                "multiple_sqla_columns = {}".format(
                    repr(multiple_sqla_columns)))

    if fulltext:
        if is_mssql:
            idxname = ''  # they are unnamed
        else:
            idxname = "_idxft_{}".format("_".join(colnames))
    else:
        idxname = "_idx_{}".format("_".join(colnames))
    if idxname and index_exists(engine, tablename, idxname):
        log.info("Skipping creation of index {} on table {}; already "
                 "exists".format(idxname, tablename))
        return
        # because it will crash if you add it again!
    log.info("Creating{ft} index {i} on table {t}, column(s) {c}".format(
        ft=" full-text" if fulltext else "",
        i=idxname or "<unnamed>",
        t=tablename,
        c=", ".join(colnames)))

    if fulltext:
        if is_mysql:
            log.info('OK to ignore this warning, if it follows next: '
                     '"InnoDB rebuilding table to add column FTS_DOC_ID"')
            # https://dev.mysql.com/doc/refman/5.6/en/innodb-fulltext-index.html
            sql = (
                "ALTER TABLE {tablename} "
                "ADD FULLTEXT INDEX {idxname} ({colnames})".format(
                    tablename=quote(tablename),
                    idxname=quote(idxname),
                    colnames=", ".join(quote(c) for c in colnames),
                )
            )
            # DDL(sql, bind=engine).execute_if(dialect=SqlaDialectName.MYSQL)
            DDL(sql, bind=engine).execute()

        elif is_mssql:  # Microsoft SQL Server
            # https://msdn.microsoft.com/library/ms187317(SQL.130).aspx
            # Argh! Complex.
            # Note that the database must also have had a
            #   CREATE FULLTEXT CATALOG somename AS DEFAULT;
            # statement executed on it beforehand.
            schemaname = engine.schema_for_object(
                sqla_table) or MSSQL_DEFAULT_SCHEMA  # noqa
            if mssql_table_has_ft_index(engine=engine,
                                        tablename=tablename,
                                        schemaname=schemaname):
                log.info(
                    "... skipping creation of full-text index on table {}; a "
                    "full-text index already exists for that table; you can "
                    "have only one full-text index per table, though it can "
                    "be on multiple columns".format(tablename))
                return
            pk_index_name = mssql_get_pk_index_name(
                engine=engine, tablename=tablename, schemaname=schemaname)
            if not pk_index_name:
                raise ValueError(
                    "To make a FULLTEXT index under SQL Server, we need to "
                    "know the name of the PK index, but couldn't find one "
                    "from get_pk_index_name() for table {}".format(
                        repr(tablename)))
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
                log.critical("SQL Server transaction count (should be 0): "
                             "{}".format(transaction_count))
                # Executing serial COMMITs or a ROLLBACK won't help here if
                # this transaction is due to Python DBAPI default behaviour.
            DDL(sql, bind=engine).execute()

            # The reversal procedure is DROP FULLTEXT INDEX ON tablename;

        else:
            log.error("Don't know how to make full text index on dialect "
                      "{}".format(engine.dialect.name))

    else:
        index = Index(idxname, sqla_column, unique=unique, mysql_length=length)
        index.create(engine)
        # Index creation doesn't require a commit.


# =============================================================================
# More DDL
# =============================================================================

def make_bigint_autoincrement_column(column_name: str,
                                     dialect: Dialect) -> Column:
    """
    Returns an instance of :class:`Column` representing a :class:`BigInteger`
    ``AUTOINCREMENT`` column in the specified :class:`Dialect`.
    """
    # noinspection PyUnresolvedReferences
    if dialect.name == SqlaDialectName.MSSQL:
        return Column(column_name, BigInteger,
                      Sequence('dummy_name', start=1, increment=1))
    else:
        # return Column(column_name, BigInteger, autoincrement=True)
        # noinspection PyUnresolvedReferences
        raise AssertionError(
            "SQLAlchemy doesn't support non-PK autoincrement fields yet for "
            "dialect {}".format(repr(dialect.name)))
        # see http://stackoverflow.com/questions/2937229


def column_creation_ddl(sqla_column: Column, dialect: Dialect) -> str:
    """
    Returns DDL to create a column, using the specified dialect.

    The column should already be bound to a table (because e.g. the SQL Server
    dialect requires this for DDL generation).

    Manual testing:
    
    .. code-block:: python

        from sqlalchemy.schema import Column, CreateColumn, MetaData, Sequence, Table
        from sqlalchemy.sql.sqltypes import BigInteger
        from sqlalchemy.dialects.mssql.base import MSDialect
        dialect = MSDialect()
        col1 = Column('hello', BigInteger, nullable=True)
        col2 = Column('world', BigInteger, autoincrement=True)  # does NOT generate IDENTITY
        col3 = Column('you', BigInteger, Sequence('dummy_name', start=1, increment=1))
        metadata = MetaData()
        t = Table('mytable', metadata)
        t.append_column(col1)
        t.append_column(col2)
        t.append_column(col3)
        print(str(CreateColumn(col1).compile(dialect=dialect)))  # hello BIGINT NULL
        print(str(CreateColumn(col2).compile(dialect=dialect)))  # world BIGINT NULL
        print(str(CreateColumn(col3).compile(dialect=dialect)))  # you BIGINT NOT NULL IDENTITY(1,1)

    If you don't append the column to a Table object, the DDL generation step
    gives:
    
    .. code-block:: none

        sqlalchemy.exc.CompileError: mssql requires Table-bound columns in order to generate DDL
    """  # noqa
    return str(CreateColumn(sqla_column).compile(dialect=dialect))


# noinspection PyUnresolvedReferences
def giant_text_sqltype(dialect: Dialect) -> str:
    """
    Returns the SQL column type used to make very large text columns for a
    given dialect.

    Args:
        dialect: a SQLAlchemy :class:`Dialect`
    Returns:
        the SQL data type of "giant text", typically 'LONGTEXT' for MySQL
        and 'NVARCHAR(MAX)' for SQL Server.
    """
    if dialect.name == SqlaDialectName.SQLSERVER:
        return 'NVARCHAR(MAX)'
    elif dialect.name == SqlaDialectName.MYSQL:
        return 'LONGTEXT'
    else:
        raise ValueError("Unknown dialect: {}".format(dialect.name))


# =============================================================================
# SQLAlchemy column types
# =============================================================================

# -----------------------------------------------------------------------------
# Reverse a textual SQL column type to an SQLAlchemy column type
# -----------------------------------------------------------------------------

RE_MYSQL_ENUM_COLTYPE = re.compile(r'ENUM\((?P<valuelist>.+)\)')
RE_COLTYPE_WITH_COLLATE = re.compile(r'(?P<maintype>.+) COLLATE .+')
RE_COLTYPE_WITH_ONE_PARAM = re.compile(r'(?P<type>\w+)\((?P<size>\w+)\)')
RE_COLTYPE_WITH_TWO_PARAMS = re.compile(
    r'(?P<type>\w+)\((?P<size>\w+),\s*(?P<dp>\w+)\)')


# http://www.w3schools.com/sql/sql_create_table.asp


def _get_sqla_coltype_class_from_str(coltype: str,
                                     dialect: Dialect) -> Type[TypeEngine]:
    """
    Returns the SQLAlchemy class corresponding to a particular SQL column
    type in a given dialect.

    Performs an upper- and lower-case search.
    For example, the SQLite dialect uses upper case, and the
    MySQL dialect uses lower case.
    """
    # noinspection PyUnresolvedReferences
    ischema_names = dialect.ischema_names
    try:
        return ischema_names[coltype.upper()]
    except KeyError:
        return ischema_names[coltype.lower()]


def get_list_of_sql_string_literals_from_quoted_csv(x: str) -> List[str]:
    """
    Used to extract SQL column type parameters. For example, MySQL has column
    types that look like ``ENUM('a', 'b', 'c', 'd')``. This function takes the
    ``"'a', 'b', 'c', 'd'"`` and converts it to ``['a', 'b', 'c', 'd']``.
    """
    f = io.StringIO(x)
    reader = csv.reader(f, delimiter=',', quotechar="'", quoting=csv.QUOTE_ALL,
                        skipinitialspace=True)
    for line in reader:  # should only be one
        return [x for x in line]


@lru_cache(maxsize=None)
def get_sqla_coltype_from_dialect_str(coltype: str,
                                      dialect: Dialect) -> TypeEngine:
    """
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
      http://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html

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
    size = None  # type: int
    dp = None  # type: int
    args = []  # type: List[Any]
    kwargs = {}  # type: Dict[str, Any]
    basetype = ''

    # noinspection PyPep8,PyBroadException
    try:
        # Split e.g. "VARCHAR(32) COLLATE blah" into "VARCHAR(32)", "who cares"
        m = RE_COLTYPE_WITH_COLLATE.match(coltype)
        if m is not None:
            coltype = m.group('maintype')

        found = False

        if not found:
            # Deal with ENUM('a', 'b', 'c', ...)
            m = RE_MYSQL_ENUM_COLTYPE.match(coltype)
            if m is not None:
                # Convert to VARCHAR with max size being that of largest enum
                basetype = 'VARCHAR'
                values = get_list_of_sql_string_literals_from_quoted_csv(
                    m.group('valuelist'))
                length = max(len(x) for x in values)
                kwargs = {'length': length}
                found = True

        if not found:
            # Split e.g. "DECIMAL(10, 2)" into DECIMAL, 10, 2
            m = RE_COLTYPE_WITH_TWO_PARAMS.match(coltype)
            if m is not None:
                basetype = m.group('type').upper()
                size = ast.literal_eval(m.group('size'))
                dp = ast.literal_eval(m.group('dp'))
                found = True

        if not found:
            # Split e.g. "VARCHAR(32)" into VARCHAR, 32
            m = RE_COLTYPE_WITH_ONE_PARAM.match(coltype)
            if m is not None:
                basetype = m.group('type').upper()
                size_text = m.group('size').strip().upper()
                if size_text != 'MAX':
                    size = ast.literal_eval(size_text)
                found = True

        if not found:
            basetype = coltype.upper()

        # Special cases: pre-processing
        # noinspection PyUnresolvedReferences
        if (dialect.name == SqlaDialectName.MSSQL and
                basetype.lower() == 'integer'):
            basetype = 'int'

        cls = _get_sqla_coltype_class_from_str(basetype, dialect)

        # Special cases: post-processing
        if basetype == 'DATETIME' and size:
            # First argument to DATETIME() is timezone, so...
            # noinspection PyUnresolvedReferences
            if dialect.name == SqlaDialectName.MYSQL:
                kwargs = {'fsp': size}
            else:
                pass
        else:
            args = [x for x in (size, dp) if x is not None]

        try:
            return cls(*args, **kwargs)
        except TypeError:
            return cls()

    except:
        # noinspection PyUnresolvedReferences
        raise ValueError("Failed to convert SQL type {} in dialect {} to an "
                         "SQLAlchemy type".format(repr(coltype),
                                                  repr(dialect.name)))


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
    if not getattr(coltype, 'collation', None):
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
        expand_for_scrubbing: bool = False) -> TypeEngine:
    """
    Converts an SQLAlchemy column type from one SQL dialect to another.

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

    # noinspection PyUnresolvedReferences
    to_mysql = dialect.name == SqlaDialectName.MYSQL
    # noinspection PyUnresolvedReferences
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
    if (isinstance(coltype, sqltypes.TIMESTAMP) and to_mssql and
            convert_mssql_timestamp):
        # You cannot write explicitly to a TIMESTAMP field in SQL Server; it's
        # used for autogenerated values only.
        # - http://stackoverflow.com/questions/10262426/sql-server-cannot-insert-an-explicit-value-into-a-timestamp-column  # noqa
        # - https://social.msdn.microsoft.com/Forums/sqlserver/en-US/5167204b-ef32-4662-8e01-00c9f0f362c2/how-to-tranfer-a-column-with-timestamp-datatype?forum=transactsql  # noqa
        #   ... suggesting BINARY(8) to store the value.
        # MySQL is more helpful:
        # - http://stackoverflow.com/questions/409286/should-i-use-field-datetime-or-timestamp  # noqa
        return mssql.base.BINARY(8)

    # -------------------------------------------------------------------------
    # Some other type
    # -------------------------------------------------------------------------
    return coltype


# =============================================================================
# Questions about SQLAlchemy column types
# =============================================================================

# Note:
#   x = String        } type(x) == VisitableType  # metaclass
#   x = BigInteger    }
# but:
#   x = String()      } type(x) == TypeEngine
#   x = BigInteger()  }
#
# isinstance also cheerfully handles multiple inheritance, i.e. if you have
# class A(object), class B(object), and class C(A, B), followed by x = C(),
# then all of isinstance(x, A), isinstance(x, B), isinstance(x, C) are True

def _coltype_to_typeengine(coltype: Union[TypeEngine,
                                          VisitableType]) -> TypeEngine:
    """
    An example is simplest: if you pass in ``Integer()`` (an instance of
    :class:`TypeEngine`), you'll get ``Integer()`` back. If you pass in
    ``Integer`` (an instance of :class:`VisitableType`), you'll also get
    ``Integer()`` back. The function asserts that its return type is an
    instance of :class:`TypeEngine`.
    """
    if isinstance(coltype, VisitableType):
        coltype = coltype()
    assert isinstance(coltype, TypeEngine)
    return coltype


def is_sqlatype_binary(coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type a binary type?
    """
    # Several binary types inherit internally from _Binary, making that the
    # easiest to check.
    coltype = _coltype_to_typeengine(coltype)
    # noinspection PyProtectedMember
    return isinstance(coltype, sqltypes._Binary)


def is_sqlatype_date(coltype: TypeEngine) -> bool:
    """
    Is the SQLAlchemy column type a date type?
    """
    coltype = _coltype_to_typeengine(coltype)
    # No longer valid in SQLAlchemy 1.2.11:
    # return isinstance(coltype, sqltypes._DateAffinity)
    return (
        isinstance(coltype, sqltypes.DateTime) or
        isinstance(coltype, sqltypes.Date)
    )


def is_sqlatype_integer(coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type an integer type?
    """
    coltype = _coltype_to_typeengine(coltype)
    return isinstance(coltype, sqltypes.Integer)


def is_sqlatype_numeric(coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type one that inherits from :class:`Numeric`,
    such as :class:`Float`, :class:`Decimal`?
    """
    coltype = _coltype_to_typeengine(coltype)
    return isinstance(coltype, sqltypes.Numeric)  # includes Float, Decimal


def is_sqlatype_string(coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type a string type?
    """
    coltype = _coltype_to_typeengine(coltype)
    return isinstance(coltype, sqltypes.String)


def is_sqlatype_text_of_length_at_least(
        coltype: Union[TypeEngine, VisitableType],
        min_length: int = 1000) -> bool:
    """
    Is the SQLAlchemy column type a string type that's at least the specified
    length?
    """
    coltype = _coltype_to_typeengine(coltype)
    if not isinstance(coltype, sqltypes.String):
        return False  # not a string/text type at all
    if coltype.length is None:
        return True  # string of unlimited length
    return coltype.length >= min_length


def is_sqlatype_text_over_one_char(
        coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type a string type that's more than one character
    long?
    """
    coltype = _coltype_to_typeengine(coltype)
    return is_sqlatype_text_of_length_at_least(coltype, 2)


def does_sqlatype_merit_fulltext_index(
        coltype: Union[TypeEngine, VisitableType],
        min_length: int = 1000) -> bool:
    """
    Is the SQLAlchemy column type a type that might merit a ``FULLTEXT``
    index (meaning a string type of at least ``min_length``)?
    """
    coltype = _coltype_to_typeengine(coltype)
    return is_sqlatype_text_of_length_at_least(coltype, min_length)


def does_sqlatype_require_index_len(
        coltype: Union[TypeEngine, VisitableType]) -> bool:
    """
    Is the SQLAlchemy column type one that requires its indexes to have a
    length specified?

    (MySQL, at least, requires index length to be specified for ``BLOB`` and
    ``TEXT`` columns:
    http://dev.mysql.com/doc/refman/5.7/en/create-index.html.)
    """
    coltype = _coltype_to_typeengine(coltype)
    if isinstance(coltype, sqltypes.Text):
        return True
    if isinstance(coltype, sqltypes.LargeBinary):
        return True
    return False


# =============================================================================
# Hack in new type
# =============================================================================

def hack_in_mssql_xml_type():
    r"""
    Modifies SQLAlchemy's type map for Microsoft SQL Server to support XML.
    
    SQLAlchemy does not support the XML type in SQL Server (mssql).
    Upon reflection, we get:
    
    .. code-block:: none
    
       sqlalchemy\dialects\mssql\base.py:1921: SAWarning: Did not recognize type 'xml' of column '...'

    We will convert anything of type ``XML`` into type ``TEXT``.

    """  # noqa
    log.debug("Adding type 'xml' to SQLAlchemy reflection for dialect 'mssql'")
    mssql.base.ischema_names['xml'] = mssql.base.TEXT
    # http://stackoverflow.com/questions/32917867/sqlalchemy-making-schema-reflection-find-use-a-custom-type-for-all-instances  # noqa

    # print(repr(mssql.base.ischema_names.keys()))
    # print(repr(mssql.base.ischema_names))


# =============================================================================
# Check column definition equality
# =============================================================================

def column_types_equal(a_coltype: TypeEngine, b_coltype: TypeEngine) -> bool:
    """
    Checks that two SQLAlchemy column types are equal (by comparing ``str()``
    versions of them).
    
    See http://stackoverflow.com/questions/34787794/sqlalchemy-column-type-comparison.
    
    IMPERFECT. 
    """  # noqa
    return str(a_coltype) == str(b_coltype)


def columns_equal(a: Column, b: Column) -> bool:
    """
    Are two SQLAlchemy columns are equal? Checks based on:

    - column ``name``
    - column ``type`` (see :func:`column_types_equal`)
    - ``nullable``
    """
    return (
        a.name == b.name and
        column_types_equal(a.type, b.type) and
        a.nullable == b.nullable
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
            log.debug("Mismatch: {} != {}".format(repr(a[i]), repr(b[i])))
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
            log.debug("Mismatch: {} != {}".format(repr(a[i]), repr(b[i])))
            return False
    return True


# =============================================================================
# Tests
# =============================================================================

def test_assert(x, y) -> None:
    try:
        assert x == y
    except AssertionError:
        print("{} should have been {}".format(repr(x), repr(y)))
        raise


def unit_tests() -> None:
    from sqlalchemy.dialects.mssql.base import MSDialect
    from sqlalchemy.dialects.mysql.base import MySQLDialect
    d_mssql = MSDialect()
    d_mysql = MySQLDialect()
    col1 = Column('hello', BigInteger, nullable=True)
    col2 = Column('world', BigInteger,
                  autoincrement=True)  # does NOT generate IDENTITY
    col3 = make_bigint_autoincrement_column('you', d_mssql)
    metadata = MetaData()
    t = Table('mytable', metadata)
    t.append_column(col1)
    t.append_column(col2)
    t.append_column(col3)

    print("Checking Column -> DDL: SQL Server (mssql)")
    test_assert(column_creation_ddl(col1, d_mssql), "hello BIGINT NULL")
    test_assert(column_creation_ddl(col2, d_mssql), "world BIGINT NULL")
    test_assert(column_creation_ddl(col3, d_mssql),
                "you BIGINT NOT NULL IDENTITY(1,1)")

    print("Checking Column -> DDL: MySQL (mysql)")
    test_assert(column_creation_ddl(col1, d_mysql), "hello BIGINT")
    test_assert(column_creation_ddl(col2, d_mysql), "world BIGINT")
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
        print("... {} -> dialect {} -> {}".format(
            repr(coltype),
            repr(dialect.name),
            repr(get_sqla_coltype_from_dialect_str(coltype, dialect))))


if __name__ == '__main__':
    unit_tests()
