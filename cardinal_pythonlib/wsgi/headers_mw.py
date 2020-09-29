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

from typing import List, Tuple

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


class AddHeadersMiddleware(object):
    """
    WSGI middleware to add arbitrary HTTP headers.
    """

    def __init__(self,
                 app: TYPE_WSGI_APP,
                 headers: List[Tuple[str, str]]) -> None:
        """
        Args:
            app:
                The WSGI app to which to apply the middleware.
            headers:
                A list of tuples, each of the form ``(key, value)``.

        See e.g. https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers for
        a list of possible HTTP headers.
        """
        assert isinstance(headers, list)
        for key_value_tuple in headers:
            assert isinstance(key_value_tuple, tuple)
            assert len(key_value_tuple) == 2
            assert isinstance(key_value_tuple[0], str)
            assert isinstance(key_value_tuple[1], str)

        self.app = app
        self.headers = headers

    def __call__(self,
                 environ: TYPE_WSGI_ENVIRON,
                 start_response: TYPE_WSGI_START_RESPONSE) \
            -> TYPE_WSGI_APP_RESULT:
        """
        Called every time the WSGI app is used.
        """

        def custom_start_response(status: TYPE_WSGI_STATUS,
                                  headers: TYPE_WSGI_RESPONSE_HEADERS,
                                  exc_info: TYPE_WSGI_EXC_INFO = None) \
                -> TYPE_WSGI_START_RESP_RESULT:
            return start_response(status, headers + self.headers, exc_info)

        return self.app(environ, custom_start_response)
