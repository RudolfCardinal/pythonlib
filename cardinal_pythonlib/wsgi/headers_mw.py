#!/usr/bin/env python
# cardinal_pythonlib/headers_mw.py

"""
===============================================================================

    Original code copyright (C) 2009-2020 Rudolf Cardinal (rudolf@pobox.com).

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

**WSGI middleware to add arbitrary HTTP headers.**

"""

import logging

from cardinal_pythonlib.wsgi.constants import (
    TYPE_WSGI_APP,
    TYPE_WSGI_APP_RESULT,
    TYPE_WSGI_ENVIRON,
    TYPE_WSGI_EXC_INFO,
    TYPE_WSGI_RESPONSE_HEADERS,
    TYPE_WSGI_START_RESPONSE,
    TYPE_WSGI_START_RESP_RESULT,
    TYPE_WSGI_STATUS,
)

log = logging.getLogger(__name__)


class HeaderModifyMode(object):
    """
    Options for
    :class:`cardinal_pythonlib.wsgi.headers_mw.AddHeadersMiddleware`.
    """
    ADD = 0
    ADD_IF_ABSENT = 1


class AddHeadersMiddleware(object):
    """
    WSGI middleware to add arbitrary HTTP headers.

    See e.g. https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers for a
    list of possible HTTP headers.

    Note:

    - HTTP headers are case-insensitive. However, the canonical form is
      hyphenated camel case;
      https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers.
    - You can specify the same HTTP header multiple times; apart from
      Set-Cookie, this should have the effect of the browser treating them as
      concatenated in a CSV format.
      https://stackoverflow.com/questions/3096888;
      https://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.2
    """

    def __init__(self,
                 app: TYPE_WSGI_APP,
                 headers: TYPE_WSGI_RESPONSE_HEADERS,
                 method: int = HeaderModifyMode.ADD) -> None:
        """
        Args:
            app:
                The WSGI app to which to apply the middleware.
            headers:
                A list of tuples, each of the form ``(key, value)``.
        """
        assert isinstance(headers, list)
        for key_value_tuple in headers:
            assert isinstance(key_value_tuple, tuple)
            assert len(key_value_tuple) == 2
            assert isinstance(key_value_tuple[0], str)
            assert isinstance(key_value_tuple[1], str)
        assert method in [
            HeaderModifyMode.ADD,
            HeaderModifyMode.ADD_IF_ABSENT,
        ]

        self.app = app
        self.headers = headers
        self.method = method

    def __call__(self,
                 environ: TYPE_WSGI_ENVIRON,
                 start_response: TYPE_WSGI_START_RESPONSE) \
            -> TYPE_WSGI_APP_RESULT:
        """
        Called every time the WSGI app is used.
        """

        def add(status: TYPE_WSGI_STATUS,
                headers: TYPE_WSGI_RESPONSE_HEADERS,
                exc_info: TYPE_WSGI_EXC_INFO = None) \
                -> TYPE_WSGI_START_RESP_RESULT:
            # Add headers. If they were present already, there will be
            # several versions now. See above.
            return start_response(status, headers + self.headers, exc_info)

        def add_if_absent(status: TYPE_WSGI_STATUS,
                          headers: TYPE_WSGI_RESPONSE_HEADERS,
                          exc_info: TYPE_WSGI_EXC_INFO = None) \
                -> TYPE_WSGI_START_RESP_RESULT:
            # Add headers, but not if that header was already present.
            # Note case-insensitivity.
            header_keys_lower = [kv[0].lower() for kv in headers]
            new_headers = [x for x in self.headers
                           if x[0].lower() not in header_keys_lower]
            return start_response(status, headers + new_headers, exc_info)

        method = self.method
        if method == HeaderModifyMode.ADD:
            custom_start_response = add
        else:
            custom_start_response = add_if_absent

        return self.app(environ, custom_start_response)
