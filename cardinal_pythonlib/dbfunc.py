#!/usr/bin/env python
# cardinal_pythonlib/dbfunc.py

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

from collections import OrderedDict
# import logging
# log = logging.getLogger(__name__)
from typing import Any, Dict, Generator, List, Optional


def get_fieldnames_from_cursor(cursor) -> List[str]:
    """
    Get fieldnames from an executed cursor.
    """
    return [i[0] for i in cursor.description]


def genrows(cursor, arraysize: int = 1000) -> Generator[List[Any], None, None]:
    """Generate all rows from a cursor."""
    # http://code.activestate.com/recipes/137270-use-generators-for-fetching-large-db-record-sets/  # noqa
    while True:
        results = cursor.fetchmany(arraysize)
        if not results:
            break
        for result in results:
            yield result


def genfirstvalues(cursor, arraysize: int = 1000) -> Generator[Any, None, None]:
    """Generate the first value in each row."""
    return (row[0] for row in genrows(cursor, arraysize))


def fetchallfirstvalues(cursor) -> List[Any]:
    """Return a list of the first value in each row."""
    return [row[0] for row in cursor.fetchall()]


def gendicts(cursor, arraysize: int = 1000) -> Generator[Dict[str, Any],
                                                         None, None]:
    """Generate all rows from a cursor as a list of OrderedDicts."""
    columns = get_fieldnames_from_cursor(cursor)
    return (
        OrderedDict(zip(columns, row))
        for row in genrows(cursor, arraysize)
    )


def dictfetchall(cursor) -> List[Dict[str, Any]]:
    """Return all rows from a cursor as a list of OrderedDicts."""
    columns = get_fieldnames_from_cursor(cursor)
    return [
        OrderedDict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def dictfetchone(cursor) -> Optional[Dict[str, Any]]:
    """
    Return the next row from a cursor as an OrderedDict, or None
    """
    columns = get_fieldnames_from_cursor(cursor)
    row = cursor.fetchone()
    if not row:
        return None
    return OrderedDict(zip(columns, row))
