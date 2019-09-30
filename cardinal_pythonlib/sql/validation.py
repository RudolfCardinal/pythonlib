#!/usr/bin/env python
# cardinal_pythonlib/sql/literals.py

"""
===============================================================================

    Original code copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).

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

**Functions to check table/column names etc. for validity in SQL.**

This is a slight

"""

import re
from typing import Optional, Tuple


# =============================================================================
# SQL types and validation
# =============================================================================

# REGEX_INVALID_TABLE_FIELD_CHARS = re.compile("[^a-zA-Z0-9_ ]")
REGEX_INVALID_TABLE_FIELD_CHARS = re.compile("[^\x20-\x7E]")
# ... SQL Server is very liberal!


def is_valid_field_name(f: Optional[str]) -> bool:
    if not f:
        return False
    if bool(REGEX_INVALID_TABLE_FIELD_CHARS.search(f)):
        return False
    return True


def is_valid_table_name(t: Optional[str]) -> bool:
    return is_valid_field_name(t)


def ensure_valid_field_name(f: Optional[str]) -> None:
    if not is_valid_field_name(f):
        raise ValueError("Field name invalid: {}".format(f))


def ensure_valid_table_name(t: Optional[str]) -> None:
    if not is_valid_table_name(t):
        raise ValueError("Table name invalid: {}".format(t))


SQLTYPES_INTEGER = [
    "INT", "INTEGER",
    "TINYINT", "SMALLINT", "MEDIUMINT", "BIGINT",
]
SQLTYPES_FLOAT = [
    "DOUBLE", "FLOAT",
]
SQLTYPES_OTHER_NUMERIC = [
    "BIT", "BOOL", "BOOLEAN", "DEC", "DECIMAL",
]
SQLTYPES_TEXT = [
    "CHAR", "VARCHAR", "NVARCHAR",
    "TINYTEXT", "TEXT", "NTEXT", "MEDIUMTEXT", "LONGTEXT",
]
SQLTYPES_BINARY = [
    "BINARY", "BLOB", "IMAGE", "LONGBLOB", "VARBINARY",
]

SQLTYPES_WITH_DATE = [
    "DATE", "DATETIME", "TIME", "TIMESTAMP",
]
SQLTYPES_DATETIME_OTHER = [
    "TIME", "YEAR",
]
SQLTYPES_DATETIME_ALL = SQLTYPES_WITH_DATE + SQLTYPES_DATETIME_OTHER

SQLTYPES_ALL = (
    SQLTYPES_INTEGER +
    SQLTYPES_FLOAT +
    SQLTYPES_OTHER_NUMERIC +
    SQLTYPES_TEXT +
    SQLTYPES_BINARY +
    SQLTYPES_DATETIME_ALL
)
# Could be more comprehensive!

SQLTYPES_NOT_TEXT = (
    SQLTYPES_INTEGER +
    SQLTYPES_FLOAT +
    SQLTYPES_OTHER_NUMERIC +
    SQLTYPES_DATETIME_ALL
)
SQLTYPES_NUMERIC = (
    SQLTYPES_INTEGER +
    SQLTYPES_FLOAT +
    SQLTYPES_OTHER_NUMERIC
)


def split_long_sqltype(datatype_long: str) -> Tuple[str, Optional[int]]:
    datatype_short = datatype_long.split("(")[0].strip()
    find_open = datatype_long.find("(")
    find_close = datatype_long.find(")")
    if 0 <= find_open < find_close:
        try:
            length = int(datatype_long[find_open + 1:find_close])
        except (TypeError, IndexError, ValueError):  # e.g. for "VARCHAR(MAX)"
            length = None
    else:
        length = None
    return datatype_short, length


def is_sqltype_valid(datatype_long: str) -> bool:
    (datatype_short, length) = split_long_sqltype(datatype_long)
    return datatype_short in SQLTYPES_ALL


def is_sqltype_date(datatype_long: str) -> bool:
    (datatype_short, length) = split_long_sqltype(datatype_long)
    return datatype_short in SQLTYPES_WITH_DATE


def is_sqltype_text(datatype_long: str) -> bool:
    (datatype_short, length) = split_long_sqltype(datatype_long)
    return datatype_short in SQLTYPES_TEXT


def is_sqltype_text_of_length_at_least(datatype_long: str,
                                       min_length: int) -> bool:
    (datatype_short, length) = split_long_sqltype(datatype_long)
    if datatype_short not in SQLTYPES_TEXT:
        return False
    if length is None:  # text, with no length, e.g. VARCHAR(MAX)
        return True
    return length >= min_length


def is_sqltype_text_over_one_char(datatype_long: str) -> bool:
    return is_sqltype_text_of_length_at_least(datatype_long, 2)


def is_sqltype_binary(datatype_long: str) -> bool:
    (datatype_short, length) = split_long_sqltype(datatype_long)
    return datatype_short in SQLTYPES_BINARY


def is_sqltype_numeric(datatype_long: str) -> bool:
    (datatype_short, length) = split_long_sqltype(datatype_long)
    return datatype_short in SQLTYPES_NUMERIC


def is_sqltype_integer(datatype_long: str) -> bool:
    (datatype_short, length) = split_long_sqltype(datatype_long)
    return datatype_short in SQLTYPES_INTEGER


def does_sqltype_require_index_len(datatype_long: str) -> bool:
    (datatype_short, length) = split_long_sqltype(datatype_long)
    return datatype_short in ["TEXT", "BLOB"]


def does_sqltype_merit_fulltext_index(datatype_long: str,
                                      min_length: int = 1000) -> bool:
    return is_sqltype_text_of_length_at_least(datatype_long, min_length)
