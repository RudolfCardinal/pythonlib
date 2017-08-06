#!/usr/bin/env python
# cardinal_pythonlib/sql/sql_grammar.py

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

from cardinal_pythonlib.sql.sql_grammar import SqlGrammar
from cardinal_pythonlib.sql.sql_grammar_mssql import SqlGrammarMSSQLServer
from cardinal_pythonlib.sql.sql_grammar_mysql import SqlGrammarMySQL


DIALECT_MSSQL = 'mssql'  # Microsoft SQL Server; must match querybuilder.js
DIALECT_MYSQL = 'mysql'  # MySQL; must match querybuilder.js
DIALECT_POSTGRES = 'postgres'  # *** NOT PROPERLY SUPPORTED.

VALID_DIALECTS = [DIALECT_MYSQL, DIALECT_MYSQL]


# =============================================================================
# Factory
# =============================================================================

mysql_grammar = SqlGrammarMySQL()
mssql_grammar = SqlGrammarMSSQLServer()


def make_grammar(dialect: str) -> SqlGrammar:
    if dialect == DIALECT_MYSQL:
        return mysql_grammar
    elif dialect == DIALECT_MSSQL:
        return mssql_grammar
    else:
        raise AssertionError("Invalid SQL dialect: {}".format(repr(dialect)))
