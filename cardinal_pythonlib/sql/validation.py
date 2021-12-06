#!/usr/bin/env python
# cardinal_pythonlib/sql/literals.py

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

**Functions to check table/column names etc. for validity in SQL.**

This is a slight

"""

import re
from typing import Optional, Tuple


# =============================================================================
# SQL types and validation: constants
# =============================================================================

# REGEX_INVALID_TABLE_FIELD_CHARS = re.compile("[^a-zA-Z0-9_ ]")
REGEX_INVALID_TABLE_FIELD_CHARS = re.compile("[^\x20-\x7E]")
# ... SQL Server is very liberal!


# - ANSI: http://jakewheat.github.io/sql-overview/sql-2011-foundation-grammar.html#predefined-type  # noqa
# - SQL Server:
#   - https://support.microsoft.com/en-us/office/equivalent-ansi-sql-data-types-7a0a6bef-ef25-45f9-8a9a-3c5f21b5c65d  # noqa
#   - https://docs.microsoft.com/en-us/sql/t-sql/data-types/data-types-transact-sql?view=sql-server-ver15  # noqa
#   - Note that ANSI "BIT" is SQL Server "BINARY".
# - MySQL: https://dev.mysql.com/doc/refman/8.0/en/data-types.html
# - PostgreSQL: https://www.postgresql.org/docs/9.5/datatype.html

SQLTYPES_INTEGER = (
    "BIGINT",  # ANSI
    "BIGSERIAL",  # PostgreSQL
    "BYTE",  # SQL Server
    "COUNTER",  # SQL Server
    "INT",  # ANSI; synonym for INTEGER
    "INT2",  # PostgreSQL
    "INT4",  # PostgreSQL synonym for INT
    "INTEGER",  # ANSI
    "INTEGER1",  # SQL Server
    "INTEGER2",  # SQL Server
    "INTEGER4",  # SQL Server
    "LONG",  # SQL Server
    "MEDIUMINT",  # MySQL
    "SERIAL",  # PostgreSQL
    "SERIAL2",  # PostgreSQL
    "SERIAL4",  # PostgreSQL
    "SHORT",  # SQL Server
    "SMALLINT",  # ANSI
    "SMALLSERIAL",  # PostgreSQL
    "TINYINT",  # SQL Server, MySQL
)
SQLTYPES_FLOAT = (
    "DOUBLE PRECISION",  # ANSI (8 bytes)
    "DOUBLE",  # SQL Server, MySQL; synonym for DOUBLE PRECISION
    "FLOAT",  # ANSI
    "FLOAT4",  # SQL Server
    "FLOAT8",  # SQL Server
    "IEEEDOUBLE",  # SQL Server
    "IEEESINGLE",  # SQL Server
    "NUMBER",  # SQL Server
    "REAL",  # ANSI (though MySQL says it is not standard)
    "SINGLE",  # SQL Server
)
SQLTYPES_OTHER_NUMERIC = (
    "BIT VARYING",  # ANSI
    "BIT",  # ANSI
    "BOOL",  # MySQL synonym for BOOLEAN or TINYINT(1)
    "BOOLEAN",  # ANSI
    "DEC",  # ANSI; synonym for DECIMAL
    "DECIMAL",  # ANSI
    "FIXED",  # MySQL; synonym for DECIMAL
    "LOGICAL",  # SQL Server
    "LOGICAL1",  # SQL Server
    "NUMERIC",  # ANSI; synonym for DECIMAL
    "ROWVERSION",  # SQL Server
    "VARBIT",  # PostgreSQL synonym for BIT VARYING
    "YESNO",  # SQL Server
)
SQLTYPES_TEXT = (
    "ALPHANUMERIC",  # SQL Server
    "CHAR LARGE OBJECT",  # ANSI
    "CHAR VARYING",  # ANSI
    "CHAR",  # ANSI
    "CHARACTER LARGE OBJECT",  # ANSI
    "CHARACTER VARYING",  # ANSI
    "CHARACTER",  # ANSI
    "CLOB",  # ANSI
    "ENUM",  # MySQL
    "LONGCHAR",  # SQL Server
    "LONGTEXT",  # SQL Server, MySQL
    "MEDIUMTEXT",  # MySQL
    "MEMO",  # SQL Server
    "NATIONAL CHAR VARYING",  # ANSI
    "NATIONAL CHAR",  # ANSI
    "NATIONAL CHARACTER LARGE OBJECT",  # ANSI
    "NATIONAL CHARACTER VARYING",  # ANSI
    "NATIONAL CHARACTER",  # ANSI
    "NCHAR LARGE OBJECT",  # ANSI
    "NCHAR VARYING",  # ANSI
    "NCHAR",  # ANSI
    "NCLOB",  # ANSI
    "NOTE",  # SQL Server
    "NTEXT",  # SQL Server
    "NVARCHAR",  # SQL Server
    "SET",  # MySQL
    "STRING",  # SQL Server
    "TEXT",  # SQL Server, MySQL
    "TINYTEXT",  # MySQL
    "VARCHAR",  # ANSI
)
SQLTYPES_BINARY = (
    "BINARY LARGE OBJECT",  # ANSI
    "BINARY VARYING",  # ANSI
    "BINARY",  # ANSI
    "BLOB",  # ANSI
    "BYTEA",  # PostgreSQL ("byte array")
    "GENERAL",  # SQL Server
    "IMAGE",  # SQL Server
    "LONGBINARY",  # SQL Server
    "LONGBLOB",  # MySQL
    "MEDIUMBLOB",  # MySQL
    "OLEOBJECT",  # SQL Server
    "TINYBLOB",  # MySQL
    "VARBINARY",  # ANSI
)
SQLTYPES_WITH_DATE = (
    "DATE",  # ANSI
    "DATETIME",  # SQL Server, MySQL
    "DATETIME2",  # SQL Server
    "DATETIMEOFFSET",  # SQL Server (date + time + time zone)
    "SMALLDATETIME",  # SQL Server
    "TIMESTAMP",  # ANSI
)
SQLTYPES_DATETIME_OTHER = (
    "INTERVAL",  # ANSI (not always supported); PostgreSQL
    "TIME",  # ANSI
    "YEAR",  # MySQL
)
SQLTYPES_OTHER = (
    "BOX",  # PostgreSQL
    "CIDR",  # PostgreSQL
    "CIRCLE",  # PostgreSQL
    "CURRENCY",  # SQL Server
    "GEOGRAPHY",  # SQL Server
    "GEOMETRY",  # SQL Server
    "GUID",  # SQL Server
    "HIERARCHYID",  # SQL Server
    "INET",  # PostgreSQL
    "JSON",  # MySQL, PostgreSQL
    "JSONB",  # PostgreSQL
    "LINE",  # PostgreSQL
    "LSEG",  # PostgreSQL
    "MACADDR",  # PostgreSQL
    "MONEY",  # SQL Server, PostgreSQL
    "PATH",  # PostgreSQL
    "PG_LSN",  # PostgreSQL
    "POINT",  # PostgreSQL
    "POLYGON",  # PostgreSQL
    "SMALLMONEY",  # SQL Server
    "SQL_VARIANT",  # SQL Server
    "TSQUERY",  # PostgreSQL
    "TSVECTOR",  # PostgreSQL
    "TXID_SNAPSHOT",  # PostgreSQL
    "UNIQUEIDENTIFIER",  # SQL Server
    "UUID",  # PostgreSQL
    "XML",  # PostgreSQL, SQL Server

    # "CURSOR",  # SQL Server, but not a *column* data type
    # "TABLE": SQL Server, but not a *column* data type
)

SQLTYPES_DATETIME_ALL = SQLTYPES_WITH_DATE + SQLTYPES_DATETIME_OTHER
SQLTYPES_ALL = (
    SQLTYPES_INTEGER +
    SQLTYPES_FLOAT +
    SQLTYPES_OTHER_NUMERIC +
    SQLTYPES_TEXT +
    SQLTYPES_BINARY +
    SQLTYPES_DATETIME_ALL +
    SQLTYPES_OTHER
)
SQLTYPES_NOT_TEXT = (
    SQLTYPES_INTEGER +
    SQLTYPES_FLOAT +
    SQLTYPES_OTHER_NUMERIC +
    SQLTYPES_DATETIME_ALL +
    SQLTYPES_OTHER
)
SQLTYPES_NUMERIC = (
    SQLTYPES_INTEGER +
    SQLTYPES_FLOAT +
    SQLTYPES_OTHER_NUMERIC
)


# =============================================================================
# SQL types and validation: functions
# =============================================================================

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
        raise ValueError(f"Field name invalid: {f}")


def ensure_valid_table_name(t: Optional[str]) -> None:
    if not is_valid_table_name(t):
        raise ValueError(f"Table name invalid: {t}")


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
