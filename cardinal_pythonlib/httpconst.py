#!/usr/bin/env python
# cardinal_pythonlib/httpconst.py

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


class MimeType(object):
    """
    Some MIME type constants.
    See also the Python standard library 'mimetypes'; e.g.

        import mimetypes
        mimetypes.types_map['.pdf']  # 'application/pdf'
    """
    PDF = "application/pdf"
    PNG = "image/png"
    SQLITE3 = "application/x-sqlite3"
    TEXT = "text/plain"
    TSV = "text/tab-separated-values"
    XML = "text/xml"
    ZIP = "application/zip"
