#!/usr/bin/env python
# cardinal_pythonlib/dbfunc.py

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

**Functions to operate with the raw Python database API.**

See https://www.python.org/dev/peps/pep-0249/.

"""

from collections import OrderedDict
# import logging
# log = logging.getLogger(__name__)
from typing import Any, Dict, Generator, List, Optional


def get_fieldnames_from_cursor(cursor) -> List[str]:
    """
    Get a list of fieldnames from an executed cursor.
    """
    return [i[0] for i in cursor.description]


def genrows(cursor, arraysize: int = 1000) -> Generator[List[Any], None, None]:
    """
    Generate all rows from a cursor.

    Args:
        cursor: the cursor
        arraysize: split fetches into chunks of this many records

    Yields:
        each row
    """
    # http://code.activestate.com/recipes/137270-use-generators-for-fetching-large-db-record-sets/  # noqa
    while True:
        results = cursor.fetchmany(arraysize)
        if not results:
            break
        for result in results:
            yield result


def genfirstvalues(cursor, arraysize: int = 1000) -> Generator[Any, None, None]:
    """
    Generate the first value in each row.

    Args:
        cursor: the cursor
        arraysize: split fetches into chunks of this many records

    Yields:
        the first value of each row
    """
    return (row[0] for row in genrows(cursor, arraysize))


def fetchallfirstvalues(cursor) -> List[Any]:
    """Return a list of the first value in each row."""
    return [row[0] for row in cursor.fetchall()]


def gendicts(cursor, arraysize: int = 1000) -> Generator[Dict[str, Any],
                                                         None, None]:
    """
    Generate all rows from a cursor as :class:`OrderedDict` objects.

    Args:
        cursor: the cursor
        arraysize: split fetches into chunks of this many records

    Yields:
        each row, as an :class:`OrderedDict` whose key are column names
        and whose values are the row values
    """
    columns = get_fieldnames_from_cursor(cursor)
    return (
        OrderedDict(zip(columns, row))
        for row in genrows(cursor, arraysize)
    )


def dictfetchall(cursor) -> List[Dict[str, Any]]:
    """
    Return all rows from a cursor as a list of :class:`OrderedDict` objects.

    Args:
        cursor: the cursor

    Returns:
        a list (one item per row) of :class:`OrderedDict` objects whose key are
        column names and whose values are the row values
    """
    columns = get_fieldnames_from_cursor(cursor)
    return [
        OrderedDict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def dictfetchone(cursor) -> Optional[Dict[str, Any]]:
    """
    Return the next row from a cursor as an :class:`OrderedDict`, or ``None``.
    """
    columns = get_fieldnames_from_cursor(cursor)
    row = cursor.fetchone()
    if not row:
        return None
    return OrderedDict(zip(columns, row))
