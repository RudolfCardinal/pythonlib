#!/usr/bin/env python
# cardinal_pythonlib/pyramid/requests.py

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

Functions to operate on Pyramid requests.

"""

import gzip
import logging
from typing import Generator
import zlib

# noinspection PyUnresolvedReferences
from pyramid.request import Request

# noinspection PyUnresolvedReferences
from webob.headers import EnvironHeaders

try:
    # noinspection PyPackageRequirements
    import brotli  # pip install brotlipy
except ImportError:
    brotli = None

log = logging.getLogger(__name__)


# =============================================================================
# Encoding checks
# =============================================================================

HTTP_ACCEPT_ENCODING = "Accept-Encoding"
HTTP_CONTENT_ENCODING = "Content-Encoding"

# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
BR_ENCODING = "br"
COMPRESS_ENCODING = "compress"
DEFLATE_ENCODING = "deflate"
GZIP_ENCODING = "gzip"
X_GZIP_ENCODING = "x-gzip"
IDENTITY_ENCODING = "identity"


def gen_accept_encoding_definitions(
    accept_encoding: str,
) -> Generator[str, None, None]:
    """
    For a given HTTP ``Accept-Encoding`` field value, generate encoding
    definitions. An example might be:

    .. code-block:: python

        from cardinal_pythonlib.pyramid.compression import *
        accept_encoding = "br;q=1.0, gzip;q=0.8, *;q=0.1"
        print(list(gen_encoding_definitions(accept_encoding)))

    which gives

    .. code-block:: none

        ['br;q=1.0', 'gzip;q=0.8', '*;q=0.1']

    """
    for definition in accept_encoding.split(","):
        yield definition.strip()


def gen_accept_encodings(accept_encoding: str) -> Generator[str, None, None]:
    """
    For a given HTTP ``Accept-Encoding`` field value, generate encodings.
    An example might be:

    .. code-block:: python

        from cardinal_pythonlib.pyramid.compression import *
        accept_encoding = "br;q=1.0, gzip;q=0.8, *;q=0.1"
        print(list(gen_encodings(accept_encoding)))

    which gives

    .. code-block:: none

        ['br', 'gzip', '*']
    """
    for definition in gen_accept_encoding_definitions(accept_encoding):
        yield definition.split(";")[0].strip()


def request_accepts_gzip(request: Request) -> bool:
    """
    Does the request specify an ``Accept-Encoding`` header that includes
    ``gzip``?

    Note:

    - Field names in HTTP headers are case-insensitive (e.g. "accept-encoding"
      is fine).
    - WebOb request headers are in a case-insensitive dictionary; see
      https://docs.pylonsproject.org/projects/webob/en/stable/. (Easily
      verified by altering the key being checked; it works.)
    - However, the value is a Python string so is case-sensitive.
    - But the HTTP standard doesn't say that field values are case-insensitive;
      see https://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.2.
    - So we'll do a case-sensitive check for "gzip".
    - But there is also a bit of other syntax possible; see
      https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Encoding.
    """  # noqa
    headers = request.headers  # type: EnvironHeaders
    if HTTP_ACCEPT_ENCODING not in headers:
        return False
    accepted_encodings = headers[HTTP_ACCEPT_ENCODING]
    for encoding in gen_accept_encodings(accepted_encodings):
        if encoding == GZIP_ENCODING:
            return True
    return False


def gen_content_encodings(request: Request) -> Generator[str, None, None]:
    """
    Generates content encodings in the order they are specified -- that is, the
    order in which they were applied.
    """
    headers = request.headers  # type: EnvironHeaders
    if HTTP_CONTENT_ENCODING not in headers:
        return
    content_encoding = headers[HTTP_CONTENT_ENCODING]
    for encoding in content_encoding.split(","):
        yield encoding.strip()


def gen_content_encodings_reversed(
    request: Request,
) -> Generator[str, None, None]:
    """
    Generates content encodings in reverse order -- that is, in the order
    required to reverse them.
    """
    for encoding in reversed(list(gen_content_encodings(request))):
        yield encoding


def decompress_request(request: Request) -> None:
    """
    Reverses anything specified in ``Content-Encoding``, modifying the request
    in place.
    """
    for encoding in gen_content_encodings_reversed(request):
        if encoding in [GZIP_ENCODING, X_GZIP_ENCODING]:
            request.body = gzip.decompress(request.body)
        elif encoding == IDENTITY_ENCODING:
            pass
        elif encoding == DEFLATE_ENCODING:
            request.body = zlib.decompress(request.body)
        elif encoding == BR_ENCODING:
            if brotli:
                # https://python-hyper.org/projects/brotlipy/en/latest/
                # noinspection PyUnresolvedReferences
                request.body = brotli.decompress(request.body)
            else:
                raise NotImplementedError(
                    f"Content-Encoding {encoding} not supported "
                    f"(brotlipy package not installed)"
                )
        else:
            raise ValueError(f"Unknown Content-Encoding: {encoding}")
            # ... e.g. "compress"; LZW; patent expired; see
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding  # noqa
