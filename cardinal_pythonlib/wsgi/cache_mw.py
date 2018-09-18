#!/usr/bin/env python
# cardinal_pythonlib/cache_mw.py

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

**WSGI middleware to disable client-side caching.**

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
log.addHandler(logging.NullHandler())
# log.setLevel(logging.DEBUG)


# =============================================================================
# DisableClientSideCachingMiddleware
# =============================================================================
# http://stackoverflow.com/questions/49547/making-sure-a-web-page-is-not-cached-across-all-browsers  # noqa
# http://stackoverflow.com/questions/3859097/how-to-add-http-headers-in-wsgi-middleware  # noqa

def add_never_cache_headers(headers: TYPE_WSGI_RESPONSE_HEADERS) -> None:
    """
    Adds WSGI headers to say "never cache this response".
    """
    headers.append(("Cache-Control", "no-cache, no-store, must-revalidate"))  # HTTP 1.1  # noqa
    headers.append(("Pragma", "no-cache"))  # HTTP 1.0
    headers.append(("Expires", "0"))  # Proxies


class DisableClientSideCachingMiddleware(object):
    """
    WSGI middleware to disable client-side caching.
    """

    def __init__(self, app: TYPE_WSGI_APP) -> None:
        self.app = app

    def __call__(self,
                 environ: TYPE_WSGI_ENVIRON,
                 start_response: TYPE_WSGI_START_RESPONSE) \
            -> TYPE_WSGI_APP_RESULT:

        def custom_start_response(status: TYPE_WSGI_STATUS,
                                  headers: TYPE_WSGI_RESPONSE_HEADERS,
                                  exc_info: TYPE_WSGI_EXC_INFO = None) \
                -> TYPE_WSGI_START_RESP_RESULT:
            add_never_cache_headers(headers)
            log.debug("HTTP status {}, headers {}".format(status, headers))
            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)
