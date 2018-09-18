#!/usr/bin/env python
# cardinal_pythonlib/errorreporter_mw.py

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

**WSGI middleware to produce tracebacks upon error.**

"""

# =============================================================================
# ErrorReportingMiddleware
# =============================================================================
# From: http://pylonsbook.com/en/1.0/the-web-server-gateway-interface-wsgi.html
# Modified to use six.StringIO
# Latest changes: 6 Jan 2016

import cgitb
# import six
from io import StringIO
import sys
from typing import List


from cardinal_pythonlib.wsgi.constants import (
    TYPE_WSGI_APP,
    TYPE_WSGI_APP_RESULT,
    TYPE_WSGI_ENVIRON,
    TYPE_WSGI_EXC_INFO,
    TYPE_WSGI_START_RESPONSE,
)


class ErrorReportingMiddleware(object):
    """
    WSGI middleware to produce ``cgitb`` traceback upon errors.
    """
    def __init__(self, app: TYPE_WSGI_APP) -> None:
        self.app = app

    @staticmethod
    def format_exception(exc_info: TYPE_WSGI_EXC_INFO) -> List[bytes]:
        dummy_file = StringIO()
        hook = cgitb.Hook(file=dummy_file)
        hook(*exc_info)
        return [dummy_file.getvalue().encode('utf-8')]

    def __call__(self,
                 environ: TYPE_WSGI_ENVIRON,
                 start_response: TYPE_WSGI_START_RESPONSE) \
            -> TYPE_WSGI_APP_RESULT:
        # noinspection PyBroadException,PyPep8
        try:
            return self.app(environ, start_response)
        except:
            exc_info = sys.exc_info()
            start_response(
                '500 Internal Server Error',
                [('content-type', 'text/html; charset=utf-8')],
                exc_info
            )
            return self.format_exception(exc_info)
