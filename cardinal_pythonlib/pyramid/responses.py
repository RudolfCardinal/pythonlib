#!/usr/bin/env python
# cardinal_pythonlib/pyramid/responses.py

"""
===============================================================================

    Original code copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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

**Specialized response types for Pyramid (which implement MIME types and
suggested download methods, etc.).**

"""

from pyramid.response import Response

from cardinal_pythonlib.httpconst import MimeType


# =============================================================================
# Responses
# =============================================================================

class BinaryResponse(Response):
    def __init__(self, body: bytes, filename: str,
                 content_type: str, as_inline: bool = False, **kwargs) -> None:
        # Inline: display within browser, if possible.
        # Attachment: download.
        disp = "inline" if as_inline else "attachment"
        super().__init__(
            content_type=content_type,
            content_disposition="{}; filename={}".format(disp, filename),
            content_encoding="binary",
            content_length=len(body),
            body=body,
            **kwargs
        )


class PdfResponse(BinaryResponse):
    def __init__(self, body: bytes, filename: str,
                 as_inline: bool = True, **kwargs) -> None:
        super().__init__(
            content_type=MimeType.PDF,
            filename=filename,
            as_inline=as_inline,
            body=body,
            **kwargs
        )


class SqliteBinaryResponse(BinaryResponse):
    def __init__(self, body: bytes, filename: str, **kwargs) -> None:
        super().__init__(
            content_type=MimeType.SQLITE3,
            filename=filename,
            body=body,
            **kwargs
        )


class TextAttachmentResponse(Response):
    def __init__(self, body: str, filename: str, **kwargs) -> None:
        # Will default to UTF-8
        super().__init__(
            content_type=MimeType.TEXT,
            content_disposition="attachment; filename={}".format(filename),
            body=body,
            **kwargs
        )


class TextResponse(Response):
    def __init__(self, body: str, **kwargs) -> None:
        super().__init__(
            content_type=MimeType.TEXT,
            body=body,
            **kwargs
        )


class TsvResponse(Response):
    def __init__(self, body: str, filename: str, **kwargs) -> None:
        super().__init__(
            content_type=MimeType.TSV,
            content_disposition="attachment; filename={}".format(filename),
            body=body,
            **kwargs
        )


class XmlResponse(Response):
    def __init__(self, body: str, **kwargs) -> None:
        # application/xml versus text/xml:
        # https://stackoverflow.com/questions/4832357
        super().__init__(
            content_type=MimeType.XML,
            body=body,
            **kwargs
        )


class ZipResponse(BinaryResponse):
    def __init__(self, body: bytes, filename: str, **kwargs) -> None:
        # For ZIP, "inline" and "attachment" dispositions are equivalent, since
        # browsers don't display ZIP files inline.
        # https://stackoverflow.com/questions/1395151
        super().__init__(
            content_type=MimeType.ZIP,
            filename=filename,
            body=body,
            **kwargs
        )
