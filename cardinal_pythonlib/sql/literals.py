#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/literals.py

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

**Functions to manipulate raw SQL.**

"""

from typing import Generator

from cardinal_pythonlib.datetimefunc import DateLikeType, DateTimeLikeType

COMMA = ","
SQUOTE = "'"
DOUBLE_SQUOTE = "''"


# =============================================================================
# SQL elements: literals
# =============================================================================

def sql_string_literal(text: str) -> str:
    """
    Transforms text into its ANSI SQL-quoted version, e.g. (in Python ``repr()``
    format):

    .. code-block:: none

        "some string"   -> "'some string'"
        "Jack's dog"    -> "'Jack''s dog'"
    """
    # ANSI SQL: http://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt
    # <character string literal>
    return SQUOTE + text.replace(SQUOTE, DOUBLE_SQUOTE) + SQUOTE


sql_quote_string = sql_string_literal  # synonym


def sql_date_literal(dt: DateLikeType) -> str:
    """
    Transforms a Python object that is of duck type ``datetime.date`` into
    an ANSI SQL literal string, like '2000-12-31'.
    """
    # ANSI SQL: http://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt
    # <date string>
    return dt.strftime("'%Y-%m-%d'")


def sql_datetime_literal(dt: DateTimeLikeType,
                         subsecond: bool = False) -> str:
    """
    Transforms a Python object that is of duck type ``datetime.datetime`` into
    an ANSI SQL literal string, like ``'2000-12-31 23:59:59'``, or if
    ``subsecond=True``, into the (non-ANSI) format
    ``'2000-12-31 23:59:59.123456'`` or similar.
    """
    # ANSI SQL: http://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt
    # <timestamp string>
    # ... the subsecond part is non-ANSI
    fmt = "'%Y-%m-%d %H:%M:%S{}'".format(".%f" if subsecond else "")
    return dt.strftime(fmt)


def sql_comment(comment: str) -> str:
    """
    Transforms a single- or multi-line string into an ANSI SQL comment,
    prefixed by ``--``.
    """
    """Using -- as a comment marker is ANSI SQL."""
    if not comment:
        return ""
    return "\n".join("-- {}".format(x) for x in comment.splitlines())


# =============================================================================
# Reversing the operations above
# =============================================================================

def sql_dequote_string(s: str) -> str:
    """
    Reverses :func:`sql_quote_string`.
    """
    if len(s) < 2 or s[0] != SQUOTE or s[-1] != SQUOTE:
        raise ValueError("Not an SQL string literal")
    s = s[1:-1]  # strip off the surrounding quotes
    return s.replace(DOUBLE_SQUOTE, SQUOTE)


# =============================================================================
# Processing SQL CSV values
# =============================================================================

def gen_items_from_sql_csv(s: str) -> Generator[str, None, None]:
    """
    Splits a comma-separated list of quoted SQL values, with ``'`` as the quote
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
