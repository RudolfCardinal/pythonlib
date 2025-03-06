#!/usr/bin/env python
# cardinal_pythonlib/excel.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

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

**Functions for dealing with Excel spreadsheets.**

"""

# =============================================================================
# Imports
# =============================================================================

import datetime
import io
from typing import Any
import uuid

from numpy import float64
from openpyxl import Workbook
from pendulum.datetime import DateTime
from semantic_version import Version


# =============================================================================
# Constants
# =============================================================================

# ISO 8601, e.g. 2013-07-24T20:04:07+0100)
ISO8601_STRFTIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


# =============================================================================
# Conversion functions
# =============================================================================


def excel_to_bytes(wb: Workbook) -> bytes:
    """
    Obtain a binary version of an :class:`openpyxl.Workbook` representation of
    an Excel file.
    """
    memfile = io.BytesIO()
    wb.save(memfile)
    return memfile.getvalue()


def convert_for_openpyxl(x: Any) -> Any:
    """
    Converts known "unusual" data types to formats suitable for ``openpyxl``.
    Specifically, handles:

    - :class:`pendulum.datetime.DateTime`
    - :class:`semantic_version.Version`
    - :class:`uuid.UUID`

    Args:
        x: a data value

    Returns:
        the same thing, or a more suitable value!

    2025-03-06 update: We were doing this:

    .. code-block:: python

        if isinstance(x, DateTime):
            return pendulum_to_datetime(x)

    However, conversion of pendulum.datetime.Datetime to datetime.datetime is
    insufficient, because with openpyxl==3.0.7 you can still end up with this
    error from openpyxl/utils/datetime.py, line 97, in to_excel:

    .. code-block:: python

        days = (dt - epoch).days
        # TypeError: can't subtract offset-naive and offset-aware datetimes

    The "epoch" variable does NOT have a timezone attribute. So we need to
    ensure that what we produce here doesn't, either. In principle, there are
    three alternatives: (a) convert to a standard timezone (UTC), making things
    slightly and silently unhappier for those working outside UTC; (b) strip
    timezone information, causing errors if datetime values are subtracted; or
    (c) convert to a standard textual representation, including timezone
    information, preserving all data but letting the user sort out the meaning.
    Since ``convert_for_pyexcel_ods3`` was already converting
    pendulum.datetime.DateTime and datetime.datetime values to a standard
    string, via strftime, let's do that too. Note that this also anticipates
    the deprecation of timezone-aware dates from openpyxl==3.0.7
    (https://foss.heptapod.net/openpyxl/openpyxl/-/issues/1645).
    """
    if isinstance(x, (DateTime, datetime.datetime)):
        return x.strftime(ISO8601_STRFTIME_FORMAT)
    elif isinstance(x, (Version, uuid.UUID)):
        return str(x)
    else:
        return x


def convert_for_pyexcel_ods3(x: Any) -> Any:
    """
    Converts known "unusual" data types to formats suitable for
    ``pyexcel-ods3``. Specifically, handles:

    - :class:`pendulum.datetime.DateTime`
    - :class:`datetime.datetime`
    - :class:`semantic_version.Version`
    - ``None``
    - :class:`numpy.float64`
    - :class:`uuid.UUID`
    - subclasses of `str`

    Args:
        x: a data value

    Returns:
        the same thing, or a more suitable value!

    2025-03-06 update: With pyexcel-ods3==0.6.0, we were getting a KeyError
    from pyexcel_ods3/odsw.py, in ODSSheetWriter.write_row. It does this:

    .. code-block:: python

        value_type = service.ODS_WRITE_FORMAT_COVERSION[type(cell)]

    and we had a cell that looked like 'aq' but had the type <class
    'sqlalchemy.sql.elements.quoted_name'>, a subclass of str.
    """
    if isinstance(x, (DateTime, datetime.datetime)):
        return x.strftime(ISO8601_STRFTIME_FORMAT)
    elif x is None:
        return ""
    elif isinstance(x, (Version, uuid.UUID)):
        return str(x)
    elif isinstance(x, float64):
        return float(x)
    elif isinstance(x, str):
        return str(x)
    else:
        return x
