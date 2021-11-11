#!/usr/bin/env python
# cardinal_pythonlib/compression.py

"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

Compression functions.

"""

import gzip


# =============================================================================
# gzip compression/decompression
# =============================================================================

def gzip_string(text: str, encoding: str = "utf-8") -> bytes:
    """
    Encodes a string, then compresses it with gzip.

    When you send data over HTTP and wish to compress it, what should you do?

    - Use HTTP ``Content-Encoding``;
      https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding.
    - This is defined in HTTP/1.1; see https://www.ietf.org/rfc/rfc2616.txt.
    - The gzip format is the most broadly supported, according to
      https://en.wikipedia.org/wiki/HTTP_compression.
    - This format is defined in https://www.ietf.org/rfc/rfc1952.txt.
    - The gzip format has a header; see above and
      https://en.wikipedia.org/wiki/Gzip.
    - Python's :func:`gzip.compress` writes to a memory file internally and
      writes the header.
    - So the work in the most popular answer here is unnecessary:
      https://stackoverflow.com/questions/8506897/how-do-i-gzip-compress-a-string-in-python
    - All we need is conversion of the string to bytes (via the appropriate
      encoding) and then :func:`gzip.compress`.
    - The requestor should also set HTTP ``Accept-Encoding`` if it wants
      compressed data back. See RFC2616 again (as above).

    Args:
        text:
            a string to compress
        encoding:
            encoding to use when converting string to bytes prior to
            compression

    Returns:
        bytes: gzip-compressed data

    Test code:

    .. code-block:: python

        import io
        import gzip

        teststring = "Testing; one, two, three."
        testbytes = teststring.encode("utf-8")

        gz1 = gzip.compress(testbytes)

        out1 = io.BytesIO()
        with gzip.GzipFile(fileobj=out1, mode="w") as gzfile1:
            gzfile1.write(testbytes)
        gz2 = out1.getvalue()

        print(len(gz1) == len(gz2))  # False
        print(gz1 == gz2)  # False
        # ... but the difference is probably in the timestamp bytes!

    """  # noqa
    data = text.encode(encoding)
    return gzip.compress(data)


def gunzip_string(zipped: bytes, encoding: str = "utf-8") -> str:
    """
    Reverses :func:`gzip_string`, i.e. un-gzip-compresses it, then decodes it
    into a string.

    Args:
        zipped:
            zipped data
        encoding:
            encoding that was used for the string prior to compression

    Returns:
        str: text

    Raises:
        - :exc:`OsError` if the data wasn't gzipped
        - :exc:`UnicodeDecodeError` if the decompressed data won't decode

    """
    data = gzip.decompress(zipped)
    return data.decode(encoding)
