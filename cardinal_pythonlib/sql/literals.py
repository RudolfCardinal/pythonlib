#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/literals.py

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

Functions to manipulate raw SQL.

"""

from typing import Generator

from cardinal_pythonlib.datetimefunc import DATE_LIKE_TYPE, DATETIME_LIKE_TYPE

COMMA = ","
SQUOTE = "'"


# =============================================================================
# SQL elements: literals
# =============================================================================

def sql_string_literal(text: str) -> str:
    # ANSI SQL: http://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt
    # <character string literal>
    return SQUOTE + text.replace(SQUOTE, "''") + SQUOTE


def sql_date_literal(dt: DATE_LIKE_TYPE) -> str:
    # ANSI SQL: http://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt
    # <date string>
    return dt.strftime("'%Y-%m-%d'")


def sql_datetime_literal(dt: DATETIME_LIKE_TYPE,
                         subsecond: bool = False) -> str:
    # ANSI SQL: http://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt
    # <timestamp string>
    # ... the subsecond part is non-ANSI
    fmt = "'%Y-%m-%d %H:%M:%S{}'".format(".%f" if subsecond else "")
    return dt.strftime(fmt)


def sql_comment(comment: str) -> str:
    """Using -- as a comment marker is ANSI SQL."""
    if not comment:
        return ""
    return "\n".join("-- {}".format(x) for x in comment.splitlines())


# =============================================================================
# Processing SQL CSV values
# =============================================================================

def gen_items_from_sql_csv(s: str) -> Generator[str, None, None]:
    """
    Splits a comma-separated list of quoted SQL values, with ' as the quote
    character. Allows escaping of the quote character by doubling it. Returns
    the quotes (and escaped quotes) as part of the result. Allows newlines etc.
    within the string passed.
    """
    # csv.reader will not both process the quotes and return the quotes;
    # we need them to distinguish e.g. NULL from 'NULL'.
    # log.warning('gen_items_from_sql_csv: s = {0!r}', s)
    if not s:
        return
    n = len(s)
    startpos = 0
    pos = 0
    in_quotes = False
    while pos < n:
        if not in_quotes:
            if s[pos] == COMMA:
                # end of chunk
                chunk = s[startpos:pos]  # does not include s[pos]
                result = chunk.strip()
                # log.warning('yielding: {0!r}', result)
                yield result
                startpos = pos + 1
            elif s[pos] == SQUOTE:
                # start of quote
                in_quotes = True
        else:
            if pos < n - 1 and s[pos] == SQUOTE and s[pos + 1] == SQUOTE:
                # double quote, '', is an escaped quote, not end of quote
                pos += 1  # skip one more than we otherwise would
            elif s[pos] == SQUOTE:
                # end of quote
                in_quotes = False
        pos += 1
    # Last chunk
    result = s[startpos:].strip()
    # log.warning('yielding last: {0!r}', result)
    yield result
