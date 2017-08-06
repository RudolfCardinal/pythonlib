#!/usr/bin/env python
# cardinal_pythonlib/excel.py

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


import io
import logging

from openpyxl import Workbook

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def excel_to_bytes(wb: Workbook) -> bytes:
    memfile = io.BytesIO()
    wb.save(memfile)
    return memfile.getvalue()
