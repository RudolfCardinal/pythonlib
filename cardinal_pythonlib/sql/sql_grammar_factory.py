#!/usr/bin/env python
# cardinal_pythonlib/sql/sql_grammar.py

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

**Factory to return an SQL grammer parser, given the name of an SQL dialect.**

"""

from cardinal_pythonlib.sql.sql_grammar import SqlGrammar
from cardinal_pythonlib.sql.sql_grammar_mssql import SqlGrammarMSSQLServer
from cardinal_pythonlib.sql.sql_grammar_mysql import SqlGrammarMySQL
from cardinal_pythonlib.sqlalchemy.dialect import SqlaDialectName


VALID_DIALECTS = [
    SqlaDialectName.MSSQL,
    SqlaDialectName.MYSQL,
    # PostgreSQL not properly supported yet.
]


# =============================================================================
# Factory
# =============================================================================

mysql_grammar = SqlGrammarMySQL()
mssql_grammar = SqlGrammarMSSQLServer()


def make_grammar(dialect: str) -> SqlGrammar:
    """
    Factory to make an :class:`.SqlGrammar` from the name of an SQL dialect,
    where the name is one of the members of :class:`.SqlaDialectName`.
    """
    if dialect == SqlaDialectName.MYSQL:
        return mysql_grammar
    elif dialect == SqlaDialectName.MSSQL:
        return mssql_grammar
    else:
        raise AssertionError("Invalid SQL dialect: {}".format(repr(dialect)))
