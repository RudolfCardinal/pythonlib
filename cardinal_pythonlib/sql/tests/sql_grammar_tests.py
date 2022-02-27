#!/usr/bin/env python
# cardinal_pythonlib/sql/tests/sql_grammar_tests.py

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

import logging
import re
import unittest

from pyparsing import Regex

from cardinal_pythonlib.sql.sql_grammar import (
    binary_literal,
    boolean_literal,
    date_string,
    datetime_string,
    FOR,
    hexadecimal_literal,
    integer,
    literal_value,
    numeric_literal,
    single_quote,
    string_literal,
    string_value_doublequote,
    string_value_singlequote,
    time_string,
    time_unit,
    _test_succeed,
    _test_fail,
)
from cardinal_pythonlib.sql.sql_grammar_mssql import SqlGrammarMSSQLServer
from cardinal_pythonlib.sql.sql_grammar_mysql import SqlGrammarMySQL

log = logging.getLogger(__name__)


# =============================================================================
# Tests
# =============================================================================

class SqlGrammarTests(unittest.TestCase):

    @staticmethod
    def test_base_elements() -> None:
        """
        Test basic SQL elements.
        """
        # -------------------------------------------------------------------------
        # pyparsing tests
        # -------------------------------------------------------------------------
        log.info("Testing pyparsing elements")
        regexp_for = Regex(r"\bfor\b", flags=re.IGNORECASE)
        _test_succeed(regexp_for, "for")
        _test_fail(regexp_for, "blandford")
        _test_fail(regexp_for, "upfor")
        _test_fail(regexp_for, "forename")

        # -------------------------------------------------------------------------
        # Literals
        # -------------------------------------------------------------------------
        log.info("Testing boolean_literal")
        _test_succeed(boolean_literal, "TRUE")
        _test_succeed(boolean_literal, "FALSE")
        _test_fail(boolean_literal, "blah")

        log.info("Testing binary_literal")
        _test_succeed(binary_literal, "b'010101'")
        _test_succeed(binary_literal, "0b010101")

        log.info("Testing hexadecimal_literal")
        _test_succeed(hexadecimal_literal, "X'12fac'")
        _test_succeed(hexadecimal_literal, "x'12fac'")
        _test_succeed(hexadecimal_literal, "0x12fac")

        log.info("Testing integer")
        _test_succeed(integer, "99")
        _test_succeed(integer, "-99")

        log.info("Testing numeric_literal")
        _test_succeed(numeric_literal, "45")
        _test_succeed(numeric_literal, "+45")
        _test_succeed(numeric_literal, "-45")
        _test_succeed(numeric_literal, "-45E-3")
        _test_succeed(numeric_literal, "-45E3")
        _test_succeed(numeric_literal, "-45.32")
        _test_succeed(numeric_literal, "-45.32E6")

        log.info("Testing string_value_singlequote")
        _test_succeed(string_value_singlequote, "'single-quoted string'")
        log.info("Testing string_value_doublequote")
        _test_succeed(string_value_doublequote, '"double-quoted string"')
        log.info("Testing string_literal")
        _test_succeed(string_literal, "'single-quoted string'")
        _test_succeed(string_literal, '"double-quoted string"')

        log.info("Testing date_string")
        _test_succeed(date_string, single_quote("2015-04-14"))
        _test_succeed(date_string, single_quote("20150414"))
        log.info("Testing time_string")
        _test_succeed(time_string, single_quote("15:23"))
        _test_succeed(time_string, single_quote("1523"))
        _test_succeed(time_string, single_quote("15:23:00"))
        _test_succeed(time_string, single_quote("15:23:00.1"))
        _test_succeed(time_string, single_quote("15:23:00.123456"))
        log.info("Testing datetime_string")
        _test_succeed(datetime_string,
                      single_quote("2015-04-14 15:23:00.123456"))
        _test_succeed(datetime_string,
                      single_quote("2015-04-14T15:23:00.123456"))

        log.info("Testing literal")
        _test_succeed(literal_value, "NULL")
        _test_succeed(literal_value, "99")
        _test_succeed(literal_value, "-99")

        log.info("Testing time_unit")
        _test_succeed(time_unit, "MICROSECOND")
        _test_succeed(time_unit, "year_month")

        # -------------------------------------------------------------------------
        # Identifiers
        # -------------------------------------------------------------------------

        log.info("Testing FOR")
        # print(FOR.pattern)
        _test_succeed(FOR, "for")
        _test_fail(FOR, "thingfor")  # shouldn't match FOR
        _test_fail(FOR, "forename")  # shouldn't match FOR

    @staticmethod
    def test_sqlgrammar_mssql_server() -> None:
        SqlGrammarMSSQLServer().test()

    @staticmethod
    def test_sqlgrammar_mysql() -> None:
        SqlGrammarMySQL().test()
