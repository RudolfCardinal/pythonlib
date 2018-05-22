#!/usr/bin/env python
# cardinal_pythonlib/errorreporter_mw.py

"""
===============================================================================
    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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
"""

# =============================================================================
# ErrorReportingMiddleware
# =============================================================================
# From: http://pylonsbook.com/en/1.0/the-web-server-gateway-interface-wsgi.html
# Modified to use six.StringIO
# Latest changes: 6 Jan 2016

# import six
from io import StringIO
import sys
import cgitb


class ErrorReportingMiddleware(object):
    """WSGI middleware to produce cgitb traceback."""
    def __init__(self, app):
        self.app = app

    @staticmethod
    def format_exception(exc_info):
        dummy_file = StringIO()
        hook = cgitb.Hook(file=dummy_file)
        hook(*exc_info)
        return [dummy_file.getvalue().encode('utf-8')]

    def __call__(self, environ, start_response):
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
