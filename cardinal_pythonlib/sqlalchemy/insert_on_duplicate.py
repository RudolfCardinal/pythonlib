#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/insert_on_duplicate.py

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

import logging
import re
from typing import Any

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.expression import Insert, TableClause

from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# INSERT ... ON DUPLICATE KEY UPDATE support, for MySQL
# =============================================================================
# https://www.reddit.com/r/Python/comments/p5grh/sqlalchemy_whats_the_idiomatic_way_of_writing/  # noqa
# https://github.com/bedwards/sqlalchemy_mysql_ext/blob/master/duplicate.py
# ... modified
# http://docs.sqlalchemy.org/en/rel_1_0/core/compiler.html
# http://stackoverflow.com/questions/6611563/sqlalchemy-on-duplicate-key-update
# http://dev.mysql.com/doc/refman/5.7/en/insert-on-duplicate.html
#
# Once implemented, you can do
#       q = sqla_table.insert_on_duplicate().values(destvalues)
#       session.execute(q)

# =============================================================================
# NOTE: SQLALCHEMY SUPPORTS THIS NATIVELY AS OF V1.2:
# =============================================================================
# http://docs.sqlalchemy.org/en/latest/changelog/migration_12.html
# http://docs.sqlalchemy.org/en/latest/dialects/mysql.html#mysql-insert-on-duplicate-key-update  # noqa


# noinspection PyAbstractClass
class InsertOnDuplicate(Insert):
    pass


def insert_on_duplicate(tablename: str,
                        values: Any = None,
                        inline: bool = False,
                        **kwargs):
    return InsertOnDuplicate(tablename, values, inline=inline, **kwargs)


# noinspection PyPep8Naming
def monkeypatch_TableClause() -> None:
    log.debug("Adding 'INSERT ON DUPLICATE KEY UPDATE' support for MySQL "
              "to SQLAlchemy")
    TableClause.insert_on_duplicate = insert_on_duplicate


# noinspection PyPep8Naming
def unmonkeypatch_TableClause() -> None:
    del TableClause.insert_on_duplicate


STARTSEPS = '`'
ENDSEPS = '`'
INSERT_FIELDNAMES_REGEX = (
    r'^INSERT\sINTO\s[{startseps}]?(?P<table>\w+)[{endseps}]?\s+'
    r'\((?P<columns>[, {startseps}{endseps}\w]+)\)\s+VALUES'.format(
        startseps=STARTSEPS, endseps=ENDSEPS)
)
# http://pythex.org/ !
RE_INSERT_FIELDNAMES = re.compile(INSERT_FIELDNAMES_REGEX)


@compiles(InsertOnDuplicate, SqlaDialectName.MYSQL)
def compile_insert_on_duplicate_key_update(insert: Insert,
                                           compiler: SQLCompiler,
                                           **kw) -> str:
    """
    We can't get the fieldnames directly from 'insert' or 'compiler'.
    We could rewrite the innards of the visit_insert statement, like
        https://github.com/bedwards/sqlalchemy_mysql_ext/blob/master/duplicate.py  # noqa
    ... but, like that, it will get outdated.
    We could use a hack-in-by-hand method, like
        http://stackoverflow.com/questions/6611563/sqlalchemy-on-duplicate-key-update
    ... but a little automation would be nice.
    So, regex to the rescue.
    NOTE THAT COLUMNS ARE ALREADY QUOTED by this stage; no need to repeat.
    """
    # log.critical(compiler.__dict__)
    # log.critical(compiler.dialect.__dict__)
    # log.critical(insert.__dict__)
    s = compiler.visit_insert(insert, **kw)
    # log.critical(s)
    m = RE_INSERT_FIELDNAMES.match(s)
    if m is None:
        raise ValueError("compile_insert_on_duplicate_key_update: no match")
    columns = [c.strip() for c in m.group('columns').split(",")]
    # log.critical(columns)
    updates = ", ".join(
        ["{c} = VALUES({c})".format(c=c) for c in columns])
    s += ' ON DUPLICATE KEY UPDATE {}'.format(updates)
    # log.critical(s)
    return s


_TEST_CODE = '''

from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class OrmObject(Base):
    __tablename__ = "sometable"
    id = Column(Integer, primary_key=True)
    name = Column(String)


engine = create_engine("sqlite://", echo=True)
Base.metadata.create_all(engine)

session = Session(engine)

d1 = dict(id=1, name="One")
d2 = dict(id=2, name="Two")

insert_1 = OrmObject.__table__.insert(values=d1)
insert_2 = OrmObject.__table__.insert(values=d2)
session.execute(insert_1)
session.execute(insert_2)
session.execute(insert_1)  # raises sqlalchemy.exc.IntegrityError


# ... recommended cross-platform way is SELECT then INSERT or UPDATE 
# accordingly; see
# https://groups.google.com/forum/#!topic/sqlalchemy/aQLqeHmLPQY

'''
