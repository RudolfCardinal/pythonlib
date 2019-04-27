#!/usr/bin/env python
# cardinal_pythonlib/httpconst.py

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

**Constants for use with HTTP.**

"""


class MimeType(object):
    """
    Some MIME type constants.
    See also the Python standard library ``mimetypes``; e.g.

    .. code-block:: python

        import mimetypes
        mimetypes.types_map['.pdf']  # 'application/pdf'
        
    See:
        
    - CSV
    
      - http://stackoverflow.com/questions/264256/what-is-the-best-mime-type-and-extension-to-use-when-exporting-tab-delimited
      - http://www.iana.org/assignments/media-types/text/tab-separated-values
    
    - ZIP
    
      - http://stackoverflow.com/questions/4411757/zip-mime-types-when-to-pick-which-one
      
    - Microsoft Office
    
      - https://filext.com/faq/office_mime_types.html
      
    - OpenOffice
    
      - https://www.openoffice.org/framework/documentation/mimetypes/mimetypes.html
      - https://stackoverflow.com/questions/31489757/what-is-correct-mimetype-with-apache-openoffice-files-like-odt-ods-odp

    """  # noqa
    CSV = "text/csv"
    ODS = "application/vnd.oasis.opendocument.spreadsheet"
    PDF = "application/pdf"
    PNG = "image/png"
    SQLITE3 = "application/x-sqlite3"
    TEXT = "text/plain"
    TSV = "text/tab-separated-values"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    XML = "text/xml"
    ZIP = "application/zip"
