#!/usr/bin/env python
# cardinal_pythonlib/httpconst.py

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


# =============================================================================
# HTTP methods
# =============================================================================


class HttpMethod(object):
    """
    HTTP request methods, as upper-case constants.

    - https://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html
    - https://datatracker.ietf.org/doc/html/rfc7231
    - https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol#Request_methods
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
    """

    CONNECT = "CONNECT"  # HTTP/1.1
    DELETE = "DELETE"  # HTTP/1.1
    GET = "GET"  # HTTP/1.0
    HEAD = "HEAD"  # HTTP/1.0
    OPTIONS = "OPTIONS"  # HTTP/1.1
    PATCH = "PATCH"  # HTTP/1.1
    POST = "POST"  # HTTP/1.0
    PUT = "PUT"  # HTTP/1.1
    TRACE = "TRACE"  # HTTP/1.1


# =============================================================================
# HTTP status codes
# =============================================================================


class HttpStatus(object):
    """
    HTTP status codes.

    https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
    """

    # 1xx: informational
    CONTINUE = 100
    SWITCHING_PROTOCOLS = 101
    PROCESSING = 102
    EARLY_HINTS = 103

    # 2xx: success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NON_AUTHORITATIVE_INFORMATION = 203
    NO_CONTENT = 204
    RESET_CONTENT = 205
    PARTIAL_CONTENT = 206
    MULTI_STATUS = 207
    ALREADY_REPORTED = 208
    IM_USED = 226

    # 3xx: redirection
    MULTIPLE_CHOICES = 300
    MOVED_PERMANENTLY = 301
    FOUND = 302
    SEE_OTHER = 303
    NOT_MODIFIED = 304
    USE_PROXY = 305
    SWITCH_PROXY = 306  # no longer used
    TEMPORARY_REDIRECT = 307
    PERMANENT_REDIRECT = 308

    # 4xx: client error
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    PROXY_AUTHENTICATION_REQUIRED = 407
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    GONE = 410
    LENGTH_REQUIRED = 411
    PRECONDTION_FAILED = 412
    PAYLOAD_TOO_LARGE = 413
    URI_TOO_LONG = 414
    UNSUPPORTED_MEDIA_TYPE = 415
    RANGE_NOT_SUITABLE = 416
    EXPECTATION_FAILED = 417
    IM_A_TEAPOT = 418
    MISDIRECTED_REQUEST = 421
    UNPROCESSABLE_ENTITY = 422
    LOCKED = 423
    FAILED_DEPENDENCY = 424
    TOO_EARLY = 425
    UPGRADE_REQUIRED = 426
    PRECONDITION_REQUIRED = 428
    TOO_MANY_REQUESTS = 429
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431
    UNAVAILABLE_FOR_LEGAL_REASONS = 451

    # 5xx: server error
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    HTTP_VERSION_NOT_SUPPORTED = 505
    VARIANT_ALSO_NEGOTIATES = 506
    INSUFICIENT_STORAGE = 507
    LOOP_DETECTED = 508
    NOT_EXTENDED = 510
    NETWORK_AUTHENTICATION_REQUIRED = 511

    @classmethod
    def is_good_answer(cls, status: int) -> bool:
        """
        Is the given HTTP status code a satisfactory (happy) answer to a
        client's request?
        """
        return 200 <= status <= 299 or status == cls.PROCESSING


# =============================================================================
# MIME types
# =============================================================================


class MimeType(object):
    """
    Some MIME type constants.
    See also the Python standard library ``mimetypes``; e.g.

    .. code-block:: python

        import mimetypes
        mimetypes.types_map['.pdf']  # 'application/pdf'

    See:

    - Binary:

      - https://stackoverflow.com/questions/6783921/which-mime-type-to-use-for-a-binary-file-thats-specific-to-my-program

    - CSV

      - https://stackoverflow.com/questions/264256/what-is-the-best-mime-type-and-extension-to-use-when-exporting-tab-delimited
      - https://www.iana.org/assignments/media-types/text/tab-separated-values

    - JSON:

      - https://stackoverflow.com/questions/477816/what-is-the-correct-json-content-type

    - ZIP

      - https://stackoverflow.com/questions/4411757/zip-mime-types-when-to-pick-which-one

    - Microsoft Office

      - https://filext.com/faq/office_mime_types.html

    - OpenOffice

      - https://www.openoffice.org/framework/documentation/mimetypes/mimetypes.html
      - https://stackoverflow.com/questions/31489757/what-is-correct-mimetype-with-apache-openoffice-files-like-odt-ods-odp

    """  # noqa

    BINARY = "application/octet-stream"
    CSV = "text/csv"
    DOC = "application/msword"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # noqa
    DOT = DOC
    DOTX = "application/vnd.openxmlformats-officedocument.wordprocessingml.template"  # noqa
    FORCE_DOWNLOAD = "application/force-download"
    HTML = "text/html"
    JSON = "application/json"
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
