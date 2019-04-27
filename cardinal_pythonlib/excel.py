#!/usr/bin/env python
# cardinal_pythonlib/excel.py

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

**Functions for dealing with Excel spreadsheets.**

"""

import io
from typing import Any

from openpyxl import Workbook
from pendulum.datetime import DateTime
from semantic_version import Version

from cardinal_pythonlib.datetimefunc import pendulum_to_datetime


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

    Args:
        x: a data value

    Returns:
        the same thing, or a more suitable value!
    """
    if isinstance(x, DateTime):
        return pendulum_to_datetime(x)
    elif isinstance(x, Version):
        return str(x)
    else:
        return x
