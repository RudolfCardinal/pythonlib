#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/alembic_func.py

"""
===============================================================================
    Copyright (C) 2009-2017 Rudolf Cardinal (rudolf@pobox.com).

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

from collections import Iterable
import datetime
import decimal
import logging
import os
import sys
from typing import (Any, Callable, Dict, Generator, Optional, TextIO, Tuple,
                    Union)

from alembic.config import Config
# noinspection PyUnresolvedReferences
from alembic.migration import MigrationContext
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
import arrow
# from sqlalchemy.dialects.mysql.base import MySQLDialect
from sqlalchemy.engine import Connectable, create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import class_mapper, Session, Query
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.elements import BindParameter
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.schema import MetaData, Table
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import DateTime, NullType, String, TypeDecorator
import sqlalchemy.dialects.mssql
import sqlalchemy.dialects.mysql

from cardinal_pythonlib.file_io import writelines_nl, writeline_nl

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Constants for Alembic
# =============================================================================
# https://alembic.readthedocs.org/en/latest/naming.html

ALEMBIC_NAMING_CONVENTION = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    # "ck": "ck_%(table_name)s_%(constraint_name)s",  # too long?
    # ... https://groups.google.com/forum/#!topic/sqlalchemy/SIT4D8S9dUg
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}


# =============================================================================
# Alembic revision/migration system
# =============================================================================
# http://stackoverflow.com/questions/24622170/using-alembic-api-from-inside-application-code  # noqa

def get_head_revision_from_alembic(alembic_config_filename: str,
                                   alembic_base_dir: str = None) -> str:
    """
    Ask Alembic what its head revision is.
    Arguments:
        alembic_config_filename: config filename
        alembic_base_dir: directory to start in, so relative paths in the
            config file work.
    """
    if alembic_base_dir is None:
        alembic_base_dir = os.path.dirname(alembic_config_filename)
    os.chdir(alembic_base_dir)  # so the directory in the config file works
    config = Config(alembic_config_filename)
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def get_current_revision(database_url: str) -> str:
    """
    Ask the database what its current revision is.
    """
    engine = create_engine(database_url)
    conn = engine.connect()
    mig_context = MigrationContext.configure(conn)
    return mig_context.get_current_revision()


def get_current_and_head_revision(
        database_url: str,
        alembic_config_filename: str,
        alembic_base_dir: str = None) -> Tuple[str, str]:
    # Where we are
    head_revision = get_head_revision_from_alembic(
        alembic_config_filename, alembic_base_dir)
    log.info("Intended database version: {}".format(head_revision))

    # Where we want to be
    current_revision = get_current_revision(database_url)
    log.info("Current database version: {}".format(current_revision))

    # Are we where we want to be?
    return current_revision, head_revision


def upgrade_database(alembic_config_filename: str,
                     alembic_base_dir: str = None) -> None:
    """
    Use Alembic to upgrade our database.

    See http://alembic.readthedocs.org/en/latest/api/runtime.html
    but also, in particular, site-packages/alembic/command.py
    """

    if alembic_base_dir is None:
        alembic_base_dir = os.path.dirname(alembic_config_filename)
    os.chdir(alembic_base_dir)  # so the directory in the config file works
    config = Config(alembic_config_filename)
    script = ScriptDirectory.from_config(config)

    revision = 'head'  # where we want to get to

    # noinspection PyUnusedLocal,PyProtectedMember
    def upgrade(rev, context):
        return script._upgrade_revs(revision, rev)

    log.info(
        "Upgrading database to revision '{}' using Alembic".format(revision))

    with EnvironmentContext(config,
                            script,
                            fn=upgrade,
                            as_sql=False,
                            starting_rev=None,
                            destination_rev=revision,
                            tag=None):
        script.run_env()

    log.info("Database upgrade completed")


# =============================================================================
# Info functions
# =============================================================================

def database_is_sqlite(dbsettings: Dict[str, str]) -> bool:
    database_url = dbsettings['url']
    return database_url.startswith("sqlite:")


def database_is_postgresql(dbsettings: Dict[str, str]) -> bool:
    database_url = dbsettings['url']
    return database_url.startswith("postgresql")
    # ignore colon, since things like "postgresql:", "postgresql+psycopg2:"
    # are all OK


def database_is_mysql(dbsettings: Dict[str, str]) -> bool:
    database_url = dbsettings['url']
    return database_url.startswith("mysql")


# =============================================================================
# deepcopy an SQLAlchemy object
# =============================================================================
# Use case: object X is in the database; we want to clone it to object Y,
# which we can then save to the database, i.e. copying all SQLAlchemy field
# attributes of X except its PK. We also want it to copy anything that is
# dependent upon X, i.e. traverse relationships.
#
# https://groups.google.com/forum/#!topic/sqlalchemy/wb2M_oYkQdY
# https://groups.google.com/forum/#!searchin/sqlalchemy/cascade%7Csort:date/sqlalchemy/eIOkkXwJ-Ms/JLnpI2wJAAAJ  # noqa

def walk(obj) -> Generator[object, None, None]:
    """
    Starting with a SQLAlchemy ORM object, this function walks a
    relationship tree, yielding each of the objects once.
    """
    # http://docs.sqlalchemy.org/en/latest/faq/sessions.html#faq-walk-objects
    stack = [obj]
    seen = set()
    while stack:
        obj = stack.pop(0)
        if obj in seen:
            continue
        else:
            seen.add(obj)
            yield obj
        insp = inspect(obj)
        for relationship in insp.mapper.relationships:
            related = getattr(obj, relationship.key)
            if relationship.uselist:
                stack.extend(related)
            elif related is not None:
                stack.append(related)


def copy_sqla_object(obj: object, omit_fk: bool = True) -> object:
    """
    Given an SQLAlchemy object, creates a new object (FOR WHICH THE OBJECT
    MUST SUPPORT CREATION USING __init__() WITH NO PARAMETERS), and copies
    across all attributes, omitting PKs, FKs (by default), and relationship
    attributes.
    """
    cls = type(obj)
    mapper = class_mapper(cls)
    newobj = cls()  # not: cls.__new__(cls)
    pk_keys = set([c.key for c in mapper.primary_key])
    rel_keys = set([c.key for c in mapper.relationships])
    prohibited = pk_keys | rel_keys
    if omit_fk:
        fk_keys = set([c.key for c in mapper.columns if c.foreign_keys])
        prohibited |= fk_keys
    log.debug("copy_sqla_object: skipping: {}".format(prohibited))
    for k in [p.key for p in mapper.iterate_properties
              if p.key not in prohibited]:
        try:
            value = getattr(obj, k)
            log.debug("copy_sqla_object: processing attribute {} = {}".format(
                k, value))
            setattr(newobj, k, value)
        except AttributeError:
            log.debug("copy_sqla_object: failed attribute {}".format(k))
            pass
    return newobj


def deepcopy_sqla_object(startobj: object, session: Session,
                         flush: bool = True) -> object:
    """
    For this to succeed, the object must take a __init__ call with no
    arguments. (We can't specify the required args/kwargs, since we are copying
    a tree of arbitrary objects.)
    """
    objmap = {}  # keys = old objects, values = new objects
    log.debug("deepcopy_sqla_object: pass 1: create new objects")
    # Pass 1: iterate through all objects. (Can't guarantee to get
    # relationships correct until we've done this, since we don't know whether
    # or where the "root" of the PK tree is.)
    stack = [startobj]
    while stack:
        oldobj = stack.pop(0)
        if oldobj in objmap:  # already seen
            continue
        log.debug("deepcopy_sqla_object: copying {}".format(oldobj))
        newobj = copy_sqla_object(oldobj)
        # Don't insert the new object into the session here; it may trigger
        # an autoflush as the relationships are queried, and the new objects
        # are not ready for insertion yet (as their relationships aren't set).
        # Not also the session.no_autoflush option:
        # "sqlalchemy.exc.OperationalError: (raised as a result of Query-
        # invoked autoflush; consider using a session.no_autoflush block if
        # this flush is occurring prematurely)..."
        objmap[oldobj] = newobj
        insp = inspect(oldobj)
        for relationship in insp.mapper.relationships:
            log.debug("deepcopy_sqla_object: ... relationship: {}".format(
                relationship))
            related = getattr(oldobj, relationship.key)
            if relationship.uselist:
                stack.extend(related)
            elif related is not None:
                stack.append(related)
    # Pass 2: set all relationship properties.
    log.debug("deepcopy_sqla_object: pass 2: set relationships")
    for oldobj, newobj in objmap.items():
        log.debug("deepcopy_sqla_object: newobj: {}".format(newobj))
        insp = inspect(oldobj)
        # insp.mapper.relationships is of type
        # sqlalchemy.utils._collections.ImmutableProperties, which is basically
        # a sort of AttrDict.
        for relationship in insp.mapper.relationships:
            # The relationship is an abstract object (so getting the
            # relationship from the old object and from the new, with e.g.
            # newrel = newinsp.mapper.relationships[oldrel.key],
            # yield the same object. All we need from it is the key name.
            log.debug("deepcopy_sqla_object: ... relationship: {}".format(
                relationship.key))
            related_old = getattr(oldobj, relationship.key)
            if relationship.uselist:
                related_new = [objmap[r] for r in related_old]
            elif related_old is not None:
                related_new = objmap[related_old]
            else:
                related_new = None
            log.debug("deepcopy_sqla_object: ... ... adding: {}".format(
                related_new))
            setattr(newobj, relationship.key, related_new)
    # Now we can do session insert.
    log.debug("deepcopy_sqla_object: pass 3: insert into session")
    for newobj in objmap.values():
        session.add(newobj)
    # Done
    log.debug("deepcopy_sqla_object: done")
    if flush:
        session.flush()
    return objmap[startobj]  # returns the new object matching startobj


# =============================================================================
# Dump functions: get DDL and/or data as SQL commands
# =============================================================================

def sql_comment(comment: str) -> str:
    """Using -- as a comment marker is ANSI SQL."""
    if not comment:
        return ""
    return "\n".join("-- {}".format(x) for x in comment.splitlines())


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


# noinspection PyPep8Naming
def quick_mapper(table: Table) -> object:
    # http://www.tylerlesmann.com/2009/apr/27/copying-databases-across-platforms-sqlalchemy/  # noqa
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
            elif isinstance(value, datetime.datetime):
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
        sql_comment("Data for table: {}".format(table_name)),
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
        statement = table.insert().values(row_dict_list)
        # log.debug("statement: {}".format(repr(statement)))
        # insert_str = literal_query(statement)
        insert_str = get_literal_query(statement, bind=engine)
        # NOT WORKING FOR MULTIROW INSERTS. ONLY SUBSTITUTES FIRST ROW.
        writeline_nl(fileobj, insert_str)
    else:
        for r in cursor:
            row_dict = dict(r)
            statement = table.insert(values=row_dict)
            # insert_str = literal_query(statement)
            insert_str = get_literal_query(statement, bind=engine)
            # log.debug("row_dict: {}".format(row_dict))
            # log.debug("insert_str: {}".format(insert_str))
            writeline_nl(fileobj, insert_str)
    log.debug("... done")


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
    if dialect_name == 'mysql':
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
    for part in walk(baseobj):
        dump_orm_object_as_insert_sql(engine, part, fileobj)
    bulk_insert_extras(engine.dialect.name, fileobj, start=False)


# =============================================================================
# ArrowType that uses fractional second support in MySQL
# =============================================================================

class ArrowMicrosecondType(TypeDecorator):
    """
    Based on ArrowType from SQLAlchemy-Utils, but copes with fractional seconds
    under MySQL 5.6.4+.
    """
    impl = DateTime
    # RNC: For MySQL, need to use sqlalchemy.dialects.mysql.DATETIME(fsp=6);
    # see load_dialect_impl() below.

    def load_dialect_impl(self, dialect: DefaultDialect) -> TypeEngine:  # RNC
        if dialect.name == 'mysql':
            return dialect.type_descriptor(
                sqlalchemy.dialects.mysql.DATETIME(fsp=6))
        elif dialect.name == 'mssql':  # Microsoft SQL Server
            return dialect.type_descriptor(sqlalchemy.dialects.mssql.DATETIME2)
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(
            self, value: Any,
            dialect: DefaultDialect) -> Optional[datetime.datetime]:
        if value:
            return self._coerce(value).to('UTC').naive
            # RNC: unfortunately... can't store and retrieve timezone, see docs
        return value

    def process_result_value(self, value: Any,
                             dialect: DefaultDialect) -> Optional[arrow.Arrow]:
        if value:
            return arrow.get(value)
        return value

    def process_literal_param(self, value: Any, dialect: DefaultDialect) -> str:
        return str(value)

    # noinspection PyMethodMayBeStatic
    def _coerce(self, value: Any) -> Optional[arrow.Arrow]:
        if value is None:
            return None
        elif isinstance(value, str):  # RNC
            value = arrow.get(value)
        elif isinstance(value, Iterable):
            value = arrow.get(*value)
        elif isinstance(value, datetime.datetime):  # RNC trivial change
            value = arrow.get(value)
        return value

    # noinspection PyUnusedLocal
    def coercion_listener(self, target, value, oldvalue,
                          initiator) -> Optional[arrow.Arrow]:
        return self._coerce(value)

    @property
    def python_type(self) -> type:
        # noinspection PyUnresolvedReferences
        return self.impl.type.python_type
