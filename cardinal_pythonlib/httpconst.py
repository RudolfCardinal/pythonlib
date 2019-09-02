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

Many of these can be extracted:

.. code-block:: python

    import mimetypes
    mimetypes.types_map['.zip']  # application/zip -- this is built in
    mimetypes.types_map['.xlsx']  # fails
    mimetypes.init()
    mimetypes.types_map['.xlsx']  # application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    # ... must read some local thing...
    
Something's changed -- in Python 3.6.8, there's no need for the init() call.
There is also a guessing function, :func:`mimetypes.guess_type`; see
https://docs.python.org/3.6/library/mimetypes.html.

.. code-block:: python

    >>> import mimetypes
    >>> print(mimetypes.guess_type("thing.html"))
    ('text/html', None)
    >>> print(mimetypes.guess_type("thing.xls"))
    ('application/vnd.ms-excel', None)
    >>> print(mimetypes.guess_type("thing.xlsx"))
    ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', None)

"""  # noqa


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
    DOC = "application/msword"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # noqa
    DOT = DOC
    DOTX = "application/vnd.openxmlformats-officedocument.wordprocessingml.template"  # noqa
    FORCE_DOWNLOAD = "application/force-download"
    ODP = "application/vnd.oasis.opendocument.presentation"
    ODS = "application/vnd.oasis.opendocument.spreadsheet"
    ODT = "application/vnd.oasis.opendocument.text"
    PDF = "application/pdf"
    PNG = "image/png"
    PPT = "application/vnd.ms-powerpoint"
    SQLITE3 = "application/x-sqlite3"
    TEXT = "text/plain"
    TSV = "text/tab-separated-values"
    TXT = TEXT
    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    XML = "text/xml"
    ZIP = "application/zip"


ContentType = MimeType
