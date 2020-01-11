#!/usr/bin/env python
# cardinal_pythonlib/reqest_logging_mw.py

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

**WSGI middleware to log incoming request/response details.**

"""

import logging
from typing import List, Optional

from pendulum import DateTime as Pendulum

from cardinal_pythonlib.logs import BraceStyleAdapter
from cardinal_pythonlib.wsgi.constants import (
    TYPE_WSGI_APP,
    TYPE_WSGI_APP_RESULT,
    TYPE_WSGI_ENVIRON,
    TYPE_WSGI_EXC_INFO,
    TYPE_WSGI_RESPONSE_HEADERS,
    TYPE_WSGI_START_RESPONSE,
    TYPE_WSGI_START_RESP_RESULT,
    TYPE_WSGI_STATUS,
    WsgiEnvVar,
)  # nopep8

log = BraceStyleAdapter(logging.getLogger(__name__))


class RequestLoggingMiddleware(object):
    """
    WSGI middleware to log incoming request details (+/- the response status
    code and timing information).
    """
    def __init__(self, app: TYPE_WSGI_APP,
                 logger: logging.Logger = log,
                 loglevel: int = logging.INFO,
                 show_request_immediately: bool = True,
                 show_response: bool = True,
                 show_timing: bool = True) -> None:
        """
        Args:
            app:
                The WSGI application to wrap
            logger:
                The Python logger to write to
            loglevel:
                The log level to use (e.g. ``logging.DEBUG``, ``logging.INFO``)
            show_request_immediately:
                Show the request immediately, so it's written to the log before
                the WSGI app does its processing, and is guaranteed to be
                visible even if the WSGI app hangs? The only reason to use
                ``False`` is probably if you intend to show response and/or
                timing information and you want to minimize the number of lines
                written to the log; in this case, only a single line is written
                to the log (after the wrapped WSGI app has finished
                processing).
            show_response:
                Show the HTTP response code?
            show_timing:
                Show the time that the wrapped WSGI app took?
        """
        self.app = app
        self.logger = logger
        self.loglevel = loglevel
        self.show_response = show_response
        self.show_request_immediately = show_request_immediately
        self.show_timing = show_timing
        self.two_parts = show_request_immediately and (
                show_response or show_timing)

    def log(self, msg) -> None:
        """
        Writes a message to the chosen log.
        """
        self.logger.log(self.loglevel, msg)

    def __call__(self,
                 environ: TYPE_WSGI_ENVIRON,
                 start_response: TYPE_WSGI_START_RESPONSE) \
            -> TYPE_WSGI_APP_RESULT:
        query_string = environ.get(WsgiEnvVar.QUERY_STRING, "")
        try:
            # https://stackoverflow.com/questions/7835030/obtaining-client-ip-address-from-a-wsgi-app-using-eventlet  # noqa
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For  # noqa
            forwarded_for = " [forwarded for {}]".format(
                environ[WsgiEnvVar.HTTP_X_FORWARDED_FOR])
        except KeyError:
            forwarded_for = ""
        request_details = (
            '{remote}{fwd}: "{method} {path}{qmark}{query} {proto}"'.format(
                remote=environ.get(WsgiEnvVar.REMOTE_ADDR, ""),
                fwd=forwarded_for,
                method=environ.get(WsgiEnvVar.REQUEST_METHOD, ""),
                path=environ.get(WsgiEnvVar.PATH_INFO, ""),
                qmark="?" if query_string else "",
                query=query_string,
                proto=environ.get(WsgiEnvVar.SERVER_PROTOCOL, ""),
            )
        )
        msg_parts = []  # type: List[str]
        if self.show_request_immediately:
            msg_parts.append("Request from")
            msg_parts.append(request_details)
            self.log(" ".join(msg_parts))
            msg_parts.clear()
        captured_status = None  # type: Optional[int]

        def custom_start_response(status: TYPE_WSGI_STATUS,
                                  headers: TYPE_WSGI_RESPONSE_HEADERS,
                                  exc_info: TYPE_WSGI_EXC_INFO = None) \
                -> TYPE_WSGI_START_RESP_RESULT:
            nonlocal captured_status
            captured_status = status
            return start_response(status, headers, exc_info)

        # noinspection PyBroadException
        try:
            if self.show_timing:
                t1 = Pendulum.utcnow()
            result = self.app(environ, custom_start_response)
            return result
        except Exception:
            msg_parts.append("[RAISED EXCEPTION]")
            raise
        finally:
            if self.show_request_immediately:
                msg_parts.append("Response to")
            else:
                msg_parts.append("Request from")
            msg_parts.append(request_details)
            if self.show_timing:
                t2 = Pendulum.utcnow()
            if self.show_response:
                if captured_status is not None:
                    msg_parts.append(f"-> {captured_status}")
                else:
                    msg_parts.append("[no response status]")
            if self.show_timing:
                # noinspection PyUnboundLocalVariable
                time_taken_s = (t2 - t1).total_seconds()
                msg_parts.append(f"[{time_taken_s} s]")
            if msg_parts:
                self.log(" ".join(msg_parts))
