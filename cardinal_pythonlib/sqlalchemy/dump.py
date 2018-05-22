#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/dump.py

"""
===============================================================================
    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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
"""

import datetime
import decimal
import logging
import sys
from typing import Any, Callable, Dict, TextIO, Type, Union

import pendulum
from sqlalchemy.engine import Connectable, create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.engine.default import DefaultDialect  # for type hints
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.elements import BindParameter
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.schema import MetaData, Table
from sqlalchemy.sql.sqltypes import DateTime, NullType, String

from cardinal_pythonlib.file_io import writeline_nl, writelines_nl
from cardinal_pythonlib.sql.literals import sql_comment
from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName
from cardinal_pythonlib.sqlalchemy.orm_inspect import walk_orm_tree
from cardinal_pythonlib.sqlalchemy.schema import get_table_names

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

SEP1 = sql_comment("=" * 76)
SEP2 = sql_comment("-" * 76)


# =============================================================================
# Dump functions: get DDL and/or data as SQL commands
# =============================================================================

def dump_connection_info(engine: Engine, fileobj: TextIO = sys.stdout) -> None:
    """
    Dumps some connection info. Obscures passwords.
    """
    meta = MetaData(bind=engine)
    writeline_nl(fileobj, sql_comment('Database info: {}'.format(meta)))


def dump_ddl(metadata: MetaData,
             dialect_name: str,
             fileobj: TextIO = sys.stdout,
             checkfirst: bool = True) -> None:
    """
    Sends schema-creating DDL from the metadata to the dump engine.
    This makes CREATE TABLE statements.
    If checkfirst is True, it uses CREATE TABLE IF NOT EXISTS or equivalent.
    """
    # http://docs.sqlalchemy.org/en/rel_0_8/faq.html#how-can-i-get-the-create-table-drop-table-output-as-a-string  # noqa
    # http://stackoverflow.com/questions/870925/how-to-generate-a-file-with-ddl-in-the-engines-sql-dialect-in-sqlalchemy  # noqa
    # https://github.com/plq/scripts/blob/master/pg_dump.py
    # noinspection PyUnusedLocal
    def dump(querysql, *multiparams, **params):
        compsql = querysql.compile(dialect=engine.dialect)
        writeline_nl(fileobj, "{sql};".format(sql=compsql))

    writeline_nl(fileobj,
                 sql_comment("Schema (for dialect {}):".format(dialect_name)))
    engine = create_engine('{dialect}://'.format(dialect=dialect_name),
                           strategy='mock', executor=dump)
    metadata.create_all(engine, checkfirst=checkfirst)
    # ... checkfirst doesn't seem to be working for the mock strategy...
    # http://docs.sqlalchemy.org/en/latest/core/metadata.html
    # ... does it implement a *real* check (impossible here), rather than
    # issuing CREATE ... IF NOT EXISTS?


def quick_mapper(table: Table) -> Type[DeclarativeMeta]:
    # http://www.tylerlesmann.com/2009/apr/27/copying-databases-across-platforms-sqlalchemy/  # noqa
    # noinspection PyPep8Naming
    Base = declarative_base()

    class GenericMapper(Base):
        __table__ = table

    return GenericMapper


class StringLiteral(String):
    """Teach SA how to literalize various things."""
    # http://stackoverflow.com/questions/5631078/sqlalchemy-print-the-actual-query  # noqa
    def literal_processor(self,
                          dialect: DefaultDialect) -> Callable[[Any], str]:
        super_processor = super().literal_processor(dialect)

        def process(value: Any) -> str:
            log.debug("process: {}".format(repr(value)))
            if isinstance(value, int):
                return str(value)
            if not isinstance(value, str):
                value = str(value)
            result = super_processor(value)
            if isinstance(result, bytes):
                result = result.decode(dialect.encoding)
            return result
        return process


# noinspection PyPep8Naming
def make_literal_query_fn(dialect: DefaultDialect) -> Callable[[str], str]:
    DialectClass = dialect.__class__

    # noinspection PyClassHasNoInit,PyAbstractClass
    class LiteralDialect(DialectClass):
        # http://stackoverflow.com/questions/5631078/sqlalchemy-print-the-actual-query  # noqa
        colspecs = {
            # prevent various encoding explosions
            String: StringLiteral,
            # teach SA about how to literalize a datetime
            DateTime: StringLiteral,
            # don't format py2 long integers to NULL
            NullType: StringLiteral,
        }

    def literal_query(statement: str) -> str:
        """
        NOTE: This is entirely insecure. DO NOT execute the resulting
        strings.
        """
        # http://stackoverflow.com/questions/5631078/sqlalchemy-print-the-actual-query  # noqa
        if isinstance(statement, Query):
            statement = statement.statement
        return statement.compile(
            dialect=LiteralDialect(),
            compile_kwargs={'literal_binds': True},
        ).string + ";"

    return literal_query


# noinspection PyProtectedMember
def get_literal_query(statement: Union[Query, Executable],
                      bind: Connectable = None) -> str:
    # http://stackoverflow.com/questions/5631078/sqlalchemy-print-the-actual-query  # noqa
    """
    print a query, with values filled in
    for debugging purposes *only*
    for security, you should always separate queries from their values
    please also note that this function is quite slow
    """
    # log.debug("statement: {}".format(repr(statement)))
    # log.debug("statement.bind: {}".format(repr(statement.bind)))
    if isinstance(statement, Query):
        if bind is None:
            bind = statement.session.get_bind(statement._mapper_zero_or_none())
        statement = statement.statement
    elif bind is None:
        bind = statement.bind
    if bind is None:  # despite all that
        raise ValueError("Attempt to call get_literal_query with an unbound "
                         "statement and no 'bind' parameter")

    dialect = bind.dialect
    compiler = statement._compiler(dialect)

    class LiteralCompiler(compiler.__class__):
        # noinspection PyMethodMayBeStatic
        def visit_bindparam(self,
                            bindparam: BindParameter,
                            within_columns_clause: bool = False,
                            literal_binds: bool = False,
                            **kwargs) -> str:
            return super().render_literal_bindparam(
                bindparam,
                within_columns_clause=within_columns_clause,
                literal_binds=literal_binds,
                **kwargs
            )

        # noinspection PyUnusedLocal
        def render_literal_value(self, value: Any, type_) -> str:
            """Render the value of a bind parameter as a quoted literal.

            This is used for statement sections that do not accept bind
            paramters on the target driver/database.

            This should be implemented by subclasses using the quoting services
            of the DBAPI.
            """
            if isinstance(value, str):
                value = value.replace("'", "''")
                return "'%s'" % value
            elif value is None:
                return "NULL"
            elif isinstance(value, (float, int)):
                return repr(value)
            elif isinstance(value, decimal.Decimal):
                return str(value)
            elif (isinstance(value, datetime.datetime) or
                  isinstance(value, datetime.date) or
                  isinstance(value, datetime.time) or
                  isinstance(value, pendulum.Pendulum) or
                  isinstance(value, pendulum.Date) or
                  isinstance(value, pendulum.Time)):
                # All have an isoformat() method.
                return "'{}'".format(value.isoformat())
                # return (
                #     "TO_DATE('%s','YYYY-MM-DD HH24:MI:SS')"
                #     % value.strftime("%Y-%m-%d %H:%M:%S")
                # )
            else:
                raise NotImplementedError(
                    "Don't know how to literal-quote value %r" % value)

    compiler = LiteralCompiler(dialect, statement)
    return compiler.process(statement) + ";"


def dump_table_as_insert_sql(engine: Engine,
                             table_name: str,
                             fileobj: TextIO,
                             wheredict: Dict[str, Any] = None,
                             include_ddl: bool = False,
                             multirow: bool = False) -> None:
    # http://stackoverflow.com/questions/5631078/sqlalchemy-print-the-actual-query  # noqa
    # http://docs.sqlalchemy.org/en/latest/faq/sqlexpressions.html
    # http://www.tylerlesmann.com/2009/apr/27/copying-databases-across-platforms-sqlalchemy/  # noqa
    # https://github.com/plq/scripts/blob/master/pg_dump.py
    log.info("dump_data_as_insert_sql: table_name={}".format(table_name))
    writelines_nl(fileobj, [
        SEP1,
        sql_comment("Data for table: {}".format(table_name)),
        SEP2,
        sql_comment("Filters: {}".format(wheredict)),
    ])
    dialect = engine.dialect
    if not dialect.supports_multivalues_insert:
        multirow = False
    if multirow:
        log.warning("dump_data_as_insert_sql: multirow parameter substitution "
                    "not working yet")
        multirow = False

    # literal_query = make_literal_query_fn(dialect)

    meta = MetaData(bind=engine)
    log.debug("... retrieving schema")
    table = Table(table_name, meta, autoload=True)
    if include_ddl:
        log.debug("... producing DDL")
        dump_ddl(table.metadata, dialect_name=engine.dialect.name,
                 fileobj=fileobj)
    # NewRecord = quick_mapper(table)
    # columns = table.columns.keys()
    log.debug("... fetching records")
    # log.debug("meta: {}".format(meta))  # obscures password
    # log.debug("table: {}".format(table))
    # log.debug("table.columns: {}".format(repr(table.columns)))
    # log.debug("multirow: {}".format(multirow))
    query = select(table.columns)
    if wheredict:
        for k, v in wheredict.items():
            col = table.columns.get(k)
            query = query.where(col == v)
    # log.debug("query: {}".format(query))
    cursor = engine.execute(query)
    if multirow:
        row_dict_list = []
        for r in cursor:
            row_dict_list.append(dict(r))
        # log.debug("row_dict_list: {}".format(row_dict_list))
        if row_dict_list:
            statement = table.insert().values(row_dict_list)
            # log.debug("statement: {}".format(repr(statement)))
            # insert_str = literal_query(statement)
            insert_str = get_literal_query(statement, bind=engine)
            # NOT WORKING FOR MULTIROW INSERTS. ONLY SUBSTITUTES FIRST ROW.
            writeline_nl(fileobj, insert_str)
        else:
            writeline_nl(fileobj, sql_comment("No data!"))
    else:
        found_one = False
        for r in cursor:
            found_one = True
            row_dict = dict(r)
            statement = table.insert(values=row_dict)
            # insert_str = literal_query(statement)
            insert_str = get_literal_query(statement, bind=engine)
            # log.debug("row_dict: {}".format(row_dict))
            # log.debug("insert_str: {}".format(insert_str))
            writeline_nl(fileobj, insert_str)
        if not found_one:
            writeline_nl(fileobj, sql_comment("No data!"))
    writeline_nl(fileobj, SEP2)
    log.debug("... done")


def dump_database_as_insert_sql(engine: Engine,
                                fileobj: TextIO = sys.stdout,
                                include_ddl: bool = False,
                                multirow: bool = False) -> None:
    for tablename in get_table_names(engine):
        dump_table_as_insert_sql(
            engine=engine,
            table_name=tablename,
            fileobj=fileobj,
            include_ddl=include_ddl,
            multirow=multirow
        )


def dump_orm_object_as_insert_sql(engine: Engine,
                                  obj: object,
                                  fileobj: TextIO) -> None:
    # literal_query = make_literal_query_fn(engine.dialect)
    insp = inspect(obj)
    # insp: an InstanceState
    # http://docs.sqlalchemy.org/en/latest/orm/internals.html#sqlalchemy.orm.state.InstanceState  # noqa
    # insp.mapper: a Mapper
    # http://docs.sqlalchemy.org/en/latest/orm/mapping_api.html#sqlalchemy.orm.mapper.Mapper  # noqa

    # Don't do this:
    #   table = insp.mapper.mapped_table
    # Do this instead. The method above gives you fancy data types like list
    # and Arrow on the Python side. We want the bog-standard datatypes drawn
    # from the database itself.
    meta = MetaData(bind=engine)
    table_name = insp.mapper.mapped_table.name
    # log.debug("table_name: {}".format(table_name))
    table = Table(table_name, meta, autoload=True)
    # log.debug("table: {}".format(table))

    # NewRecord = quick_mapper(table)
    # columns = table.columns.keys()
    query = select(table.columns)
    # log.debug("query: {}".format(query))
    for orm_pkcol in insp.mapper.primary_key:
        core_pkcol = table.columns.get(orm_pkcol.name)
        pkval = getattr(obj, orm_pkcol.name)
        query = query.where(core_pkcol == pkval)
    # log.debug("query: {}".format(query))
    cursor = engine.execute(query)
    row = cursor.fetchone()  # should only be one...
    row_dict = dict(row)
    # log.debug("obj: {}".format(obj))
    # log.debug("row_dict: {}".format(row_dict))
    statement = table.insert(values=row_dict)
    # insert_str = literal_query(statement)
    insert_str = get_literal_query(statement, bind=engine)
    writeline_nl(fileobj, insert_str)


def bulk_insert_extras(dialect_name: str,
                       fileobj: TextIO,
                       start: bool) -> None:
    """
    Writes bulk insert preamble (start=True) or end (start=False).
    """
    lines = []
    if dialect_name == SqlaDialectName.MYSQL:
        if start:
            lines = [
                "SET autocommit=0;",
                "SET unique_checks=0;",
                "SET foreign_key_checks=0;",
            ]
        else:
            lines = [
                "SET foreign_key_checks=1;",
                "SET unique_checks=1;",
                "COMMIT;",
            ]
    writelines_nl(fileobj, lines)


def dump_orm_tree_as_insert_sql(engine: Engine,
                                baseobj: object,
                                fileobj: TextIO) -> None:
    """
    Sends an object, and all its relations (discovered via "relationship"
    links) as INSERT commands in SQL, to fileobj.

    Problem: foreign key constraints.
    - MySQL/InnoDB doesn't wait to the end of a transaction to check FK
      integrity (which it should):
      http://stackoverflow.com/questions/5014700/in-mysql-can-i-defer-referential-integrity-checks-until-commit  # noqa
    - PostgreSQL can.
    - Anyway, slightly ugly hacks...
      https://dev.mysql.com/doc/refman/5.5/en/optimizing-innodb-bulk-data-loading.html  # noqa
    - Not so obvious how we can iterate through the list of ORM objects and
      guarantee correct insertion order with respect to all FKs.
    """
    writeline_nl(
        fileobj,
        sql_comment("Data for all objects related to the first below:"))
    bulk_insert_extras(engine.dialect.name, fileobj, start=True)
    for part in walk_orm_tree(baseobj):
        dump_orm_object_as_insert_sql(engine, part, fileobj)
    bulk_insert_extras(engine.dialect.name, fileobj, start=False)
