#!/usr/bin/env python
# cardinal_pythonlib/wsgi/reverse_proxied_mw.py

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

**Middleware to set SCRIPT_NAME environment variable etc. when behind a
reverse proxy.**

"""

import logging
from pprint import pformat
from typing import List

from cardinal_pythonlib.dicts import dict_diff, delete_keys
from cardinal_pythonlib.logs import BraceStyleAdapter
from cardinal_pythonlib.wsgi.constants import (
    TYPE_WSGI_APP,
    TYPE_WSGI_APP_RESULT,
    TYPE_WSGI_ENVIRON,
    TYPE_WSGI_START_RESPONSE,
    WsgiEnvVar,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# Helper functions for handling HTTP headers
# =============================================================================

def ip_addresses_from_xff(value: str) -> List[str]:
    """
    Returns a list of IP addresses (as strings), given the value of an HTTP
    ``X-Forwarded-For`` (or ``WSGI HTTP_X_FORWARDED_FOR``) header.

    Args:
        value:
            the value of an HTTP ``X-Forwarded-For`` (or ``WSGI
            HTTP_X_FORWARDED_FOR``) header

    Returns:
        a list of IP address as strings

    See:
    - https://en.wikipedia.org/wiki/X-Forwarded-For
    - https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For  # noqa
    - NOT THIS: http://tools.ietf.org/html/rfc7239
    """
    if not value:
        return []
    return [x.strip() for x in value.split(",")]
    # ... separator is comma-space, but let's be liberal


def first_from_xff(value: str) -> str:
    """
    Returns the first IP address from an ``X-Forwarded-For`` header; see
    :func:`ip_addresses_from_xff`.

    Args:
        value:
            the value of an HTTP ``X-Forwarded-For`` (or ``WSGI
            HTTP_X_FORWARDED_FOR``) header

    Returns:
        an IP address as a string, or ``''`` if none is found

    """
    ip_addresses = ip_addresses_from_xff(value)
    if not ip_addresses:
        return ''
    return ip_addresses[0]  # leftmost


# =============================================================================
# Middleware to set SCRIPT_NAME environment variable etc. when behind a
# reverse proxy.
# =============================================================================

EXAMPLE_APACHE_REVERSE_PROXY_CONFIG = """

    # =========================================================================
    # Mount a WSGI application, using CamCOPS as an example
    # =========================================================================
    # This WSGI application is served by a SEPARATE web server (e.g. CherryPy);
    # Apache just needs to pass information to and fro, and handle the HTTPS 
    # aspects.

        # ---------------------------------------------------------------------
        # 1. Proxy requests to the external server and back, and allow access.
        # ---------------------------------------------------------------------
        # ... either via port 8000
        # ... or, better, socket /tmp/.camcops.sock
        # NOTES
        # - Don't specify trailing slashes.
        #   If you do, http://host/camcops will fail, though
        #              http://host/camcops/ will succeed.
        # - Using a socket
        #   - this requires Apache 2.4.9, and passes after the '|' character a
        #     URL that determines the Host: value of the request; see
        #       https://httpd.apache.org/docs/trunk/mod/mod_proxy.html#proxypass
        #   - The Django debug toolbar will then require the bizarre entry in
        #     the Django settings: INTERNAL_IPS = ("b''", ) -- i.e. the string
        #     value of "b''", not an empty bytestring.
        # - Ensure that you put the CORRECT PROTOCOL (e.g. https) in the rules
        #   below.
    
        # (a) Proxy    
    
        # ... via a port
        # Note the use of "http" (reflecting the backend), not https (like the
        # front end).
    ProxyPass /camcops http://127.0.0.1:8000 retry=0
    ProxyPassReverse /camcops http://127.0.0.1:8000 retry=0

        # ... or via a socket (Apache 2.4.9 and higher)
    # ProxyPass /camcops unix:/tmp/.camcops.sock|https://localhost retry=0
    # ProxyPassReverse /camcops unix:/tmp/.camcops.sock|https://localhost retry=0

        # (b) Allow proxy over SSL.
        # Without this, you will get errors like:
        #   ... SSL Proxy requested for wombat:443 but not enabled [Hint: SSLProxyEngine]
        #   ... failed to enable ssl support for 0.0.0.0:0 (httpd-UDS)
    SSLProxyEngine on
    
    <Location /camcops>
            # (c) Allow access
        Require all granted

            # (d) Tell the proxied application that we are using HTTPS:
            # ... https://stackoverflow.com/questions/16042647
            # Enable mod_headers (e.g. "sudo a2enmod headers") and:
        RequestHeader set X-Forwarded-Proto https
        RequestHeader set X-Script-Name /camcops
    </Location>

        # ---------------------------------------------------------------------
        # 2. Serve static files
        # ---------------------------------------------------------------------
        # a) offer them at the appropriate URL
        # b) provide permission

    Alias /camcops/static/ /usr/share/camcops/server/static/

    #   Change this: aim the alias at your own institutional logo.
    # Alias /camcops/static/logo_local.png /usr/share/camcops/server/static/logo_local.png

    <Directory /usr/share/camcops/server/static>
        Require all granted
    </Directory>

"""  # noqa


class ReverseProxiedConfig(object):
    """
    Class to hold information about a reverse proxy configuration.
    """
    def __init__(self,
                 trusted_proxy_headers: List[str] = None,
                 http_host: str = None,
                 remote_addr: str = None,
                 script_name: str = None,
                 server_name: str = None,
                 server_port: int = None,
                 url_scheme: str = None,
                 rewrite_path_info: bool = False) -> None:
        """
        Args:
            trusted_proxy_headers:
                list of headers, from
                :const:`ReverseProxiedMiddleware.ALL_CANDIDATES`, that the
                middleware will treat as trusted and obey. All others from this
                list will be stripped.

            http_host:
                Value to write to the ``HTTP_HOST`` WSGI variable. If not
                specified, an appropriate trusted header will be used (if there
                is one).

            remote_addr:
                ... similarly for ``REMOTE_ADDR``

            script_name:
                ... similarly for ``SCRIPT_NAME``

            server_name:
                ... similarly for ``SERVER_NAME``

            server_port:
                ... similarly for ``SERVER_PORT``

            url_scheme:
                ... similarly for ``URL_SCHEME`` (e.g. ``"https"``)

            rewrite_path_info:
                If ``True``, then if the middleware sets ``SCRIPT_NAME`` and
                ``PATH_INFO`` starts with ``SCRIPT_NAME``, the ``SCRIPT_NAME``
                will be stripped off the front of ``PATH_INFO``.

                This is appropriate for front-end web servers that fail to
                rewrite the incoming URL properly. (Do not use for Apache with
                ``ProxyPass``; ``ProxyPass`` rewrites the URLs properly for
                you.)

                ... as per e.g. http://flask.pocoo.org/snippets/35/
        """
        self.trusted_proxy_headers = []  # type: List[str]
        if trusted_proxy_headers:
            for x in trusted_proxy_headers:
                h = x.upper()
                if h in ReverseProxiedMiddleware.ALL_CANDIDATES:
                    self.trusted_proxy_headers.append(h)
        self.http_host = http_host
        self.remote_addr = remote_addr
        self.script_name = script_name.rstrip("/") if script_name else ""
        self.server_name = server_name
        self.server_port = str(server_port) if server_port is not None else ""
        self.url_scheme = url_scheme.lower() if url_scheme else ""
        self.rewrite_path_info = rewrite_path_info

    def necessary(self) -> bool:
        """
        Is any special handling (e.g. the addition of
        :class:`ReverseProxiedMiddleware`) necessary for thie config?
        """
        return any([
            self.trusted_proxy_headers,
            self.http_host,
            self.remote_addr,
            self.script_name,
            self.server_name,
            self.server_port,
            self.url_scheme,
            self.rewrite_path_info,
        ])


class ReverseProxiedMiddleware(object):
    """
    WSGI middleware to set the ``SCRIPT_NAME`` and ``PATH_INFO`` WSGI
    environment variables (etc.) correctly when behind a reverse proxy.
    
    Note that the WSGI environment variables ``HTTP_*`` are clones of HTTP
    headers; for example, ``X-Forwarded-For`` in HTTP becomes
    ``HTTP_X_FORWARDED_FOR`` in WSGI.

    See also:
        
    - http://flask.pocoo.org/snippets/35/
    - http://blog.macuyiko.com/post/2016/fixing-flask-url_for-when-behind-mod_proxy.html
    - http://alex.eftimie.ro/2013/03/21/how-to-run-flask-application-in-a-subpath-using-apache-mod_proxy/
    - http://modwsgi.readthedocs.io/en/develop/release-notes/version-4.4.9.html
    - https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers
    """  # noqa

    CANDIDATES_HTTP_HOST = [
        # These are variables that may contain a value for HTTP_HOST.
        WsgiEnvVar.HTTP_X_HOST,
        WsgiEnvVar.HTTP_X_FORWARDED_HOST
    ]
    CANDIDATES_SERVER_PORT = [
        # These are variables that may contain a value for SERVER_PORT.
        WsgiEnvVar.HTTP_X_FORWARDED_PORT
    ]
    CANDIDATES_REMOTE_ADDR = [
        # These are variables that may contain a value for REMOTE_ADDR.
        # However, they differ:
        WsgiEnvVar.HTTP_X_FORWARDED_FOR,  # may contain many values; first is taken  # noqa
        WsgiEnvVar.HTTP_X_REAL_IP  # may contain only one
    ]
    _CANDIDATES_URL_SCHEME_GIVING_PROTOCOL = [
        # These are variables whose values might be "http" or "https",
        # relevant to wsgi.url_scheme.
        WsgiEnvVar.HTTP_X_FORWARDED_PROTO,
        WsgiEnvVar.HTTP_X_FORWARDED_PROTOCOL,
        WsgiEnvVar.HTTP_X_FORWARDED_SCHEME,
        WsgiEnvVar.HTTP_X_SCHEME
    ]
    _CANDIDATES_URL_SCHEME_INDICATING_HTTPS = [
        # These are variables whose values might be "On", "True", or "1",
        # to indicate the use of HTTPS/SSL, relevant to wsgi.url_scheme.
        WsgiEnvVar.HTTP_X_FORWARDED_HTTPS,
        WsgiEnvVar.HTTP_X_FORWARDED_SSL,
        WsgiEnvVar.HTTP_X_HTTPS,
    ]
    CANDIDATES_URL_SCHEME = (
        # All variables that may inform wsgi.url_scheme
        _CANDIDATES_URL_SCHEME_GIVING_PROTOCOL +
        _CANDIDATES_URL_SCHEME_INDICATING_HTTPS
    )
    CANDIDATES_SCRIPT_NAME = [
        # These are variables that may contain a value for SCRIPT_NAME.
        WsgiEnvVar.HTTP_X_SCRIPT_NAME,
        WsgiEnvVar.HTTP_X_FORWARDED_SCRIPT_NAME
    ]
    CANDIDATES_SERVER_NAME = [
        # These are variables that may contain a value for SERVER_NAME.
        WsgiEnvVar.HTTP_X_FORWARDED_SERVER
    ]
    ALL_CANDIDATES = (
        # All variables of interest.
        CANDIDATES_HTTP_HOST +
        CANDIDATES_SERVER_PORT +
        CANDIDATES_REMOTE_ADDR +
        _CANDIDATES_URL_SCHEME_GIVING_PROTOCOL +
        _CANDIDATES_URL_SCHEME_INDICATING_HTTPS +
        CANDIDATES_SCRIPT_NAME +
        CANDIDATES_SERVER_NAME
    )
    SCHEME_HTTPS = 'https'
    TRUE_VALUES_LOWER_CASE = ["on", "true", "1"]

    def __init__(self,
                 app: TYPE_WSGI_APP,
                 config: ReverseProxiedConfig,
                 debug: bool = False) -> None:
        self.app = app
        self.config = config
        self.debug = debug

        self.vars_host = [x for x in self.CANDIDATES_HTTP_HOST
                          if x in config.trusted_proxy_headers]
        self.vars_addr = [x for x in self.CANDIDATES_REMOTE_ADDR
                          if x in config.trusted_proxy_headers]
        self.vars_script = [x for x in self.CANDIDATES_SCRIPT_NAME
                            if x in config.trusted_proxy_headers]
        self.vars_server = [x for x in self.CANDIDATES_SERVER_NAME
                            if x in config.trusted_proxy_headers]
        self.vars_port = [x for x in self.CANDIDATES_SERVER_PORT
                          if x in config.trusted_proxy_headers]
        self.vars_scheme_a = [
            x for x in self._CANDIDATES_URL_SCHEME_GIVING_PROTOCOL
            if x in config.trusted_proxy_headers
        ]
        self.vars_scheme_b = [
            x for x in self._CANDIDATES_URL_SCHEME_INDICATING_HTTPS
            if x in config.trusted_proxy_headers
        ]

        if self.debug:
            log.debug("ReverseProxiedMiddleware installed")
            self._report(WsgiEnvVar.HTTP_HOST, config.http_host,
                         self.vars_host)
            self._report(WsgiEnvVar.REMOTE_ADDR, config.remote_addr,
                         self.vars_addr)
            self._report(WsgiEnvVar.SCRIPT_NAME, config.script_name,
                         self.vars_script)
            if config.script_name or self.vars_script:
                log.debug("... which will also affect WSGI environment "
                          "variable {}", WsgiEnvVar.PATH_INFO)
            self._report(WsgiEnvVar.SERVER_NAME, config.server_name,
                         self.vars_server)
            self._report(WsgiEnvVar.SERVER_PORT, config.server_port,
                         self.vars_port)
            self._report(WsgiEnvVar.WSGI_URL_SCHEME, config.url_scheme,
                         self.vars_scheme_a + self.vars_scheme_b)

    @staticmethod
    def _report(option: str, value: str, envvars: List[str]) -> None:
        if value:
            log.debug("... WSGI environment variable {} will be set to "
                      "{}".format(option, value))
        elif envvars:
            log.debug("... WSGI environment variable {} will be set according "
                      "to reflect environment variables {!r} in "
                      "incoming requests".format(option, envvars))
        else:
            log.debug("... WSGI environment variable {} will not be "
                      "changed".format(option))

    @classmethod
    def _get_first(cls,
                   environ: TYPE_WSGI_ENVIRON,
                   envvars: List[str],
                   keys_to_keep: List[str],
                   as_remote_addr: bool = False) -> str:
        for k in envvars:
            value = environ.get(k, '')
            if value:
                keys_to_keep.append(k)
                # Oddity for REMOTE_ADDR and X-Forwarded-For:
                if as_remote_addr and k == WsgiEnvVar.HTTP_X_FORWARDED_FOR:
                    value = first_from_xff(value)
                return value
        return ''

    @classmethod
    def _proto_if_one_true(cls,
                           environ: TYPE_WSGI_ENVIRON,
                           envvars: List[str],
                           keys_to_keep: List[str]) -> str:
        for k in envvars:
            value = environ.get(k, '')
            if value.lower() in cls.TRUE_VALUES_LOWER_CASE:
                keys_to_keep.append(k)
                return cls.SCHEME_HTTPS
        return ''

    def __call__(self,
                 environ: TYPE_WSGI_ENVIRON,
                 start_response: TYPE_WSGI_START_RESPONSE) \
            -> TYPE_WSGI_APP_RESULT:
        """
        -----------------------------------------------------------------------
        REWRITING THE HOST (setting HTTP_HOST):
        -----------------------------------------------------------------------

        If you don't rewrite the host, the Pyramid debug toolbar will get
        things a bit wrong. An example:
            http://127.0.0.1:80/camcops
        is proxied by Apache to
            http://127.0.0.7:8000/camcops

        In that situation, HTTP_HOST will be '127.0.0.1:8000', and so the
        Pyramid debug toolbar will start asking the web browser to go to
            http://127.0.0.1:8000/camcops/_debug_toolbar/...
        ... which is wrong (it's a reference to the "internal" site).

        If you allow the host to be rewritten, then you get a sensible
        reference e.g. to
            http://wombat/camcops/_debug_toolbar/...

        Should we be looking at HTTP_X_FORWARDED_HOST or
        HTTP_X_FORWARDED_SERVER?
        See https://github.com/omnigroup/Apache/blob/master/httpd/modules/proxy/mod_proxy_http.c  # noqa
        ... and let's follow mod_wsgi.

        -----------------------------------------------------------------------
        HTTP_HOST versus SERVER_NAME
        -----------------------------------------------------------------------
        https://stackoverflow.com/questions/2297403/what-is-the-difference-between-http-host-and-server-name-in-php  # noqa

        -----------------------------------------------------------------------
        REWRITING THE PROTOCOL
        -----------------------------------------------------------------------
        Consider how we get here. For example, we may have this sequence:

            user's web browser
            -> Apache front-end web server via HTTPS on port 443
                -> ProxyPass/ProxyPassReverse
            -> CherryPy server via HTTP on port 8000 or via a Unix socket
                -> ...
                -> cherrypy/wsgiserver/__init__.py,
                    WSGIGateway_10.get_environ()
                    ... which creates a WSGI environment from an HTTP request.

        So if you want to see what's coming by way of raw headers, put this
        in at the end of that get_environ() function:

            from pprint import pformat; import logging; log = logging.getLogger(__name__); log.critical("Request headers:\n" + pformat(req.inheaders))  # noqa

        """
        if self.debug:
            log.debug("Starting WSGI environment: \n{}", pformat(environ))
            oldenv = environ.copy()
        keys_to_keep = []  # type: List[str]
        config = self.config

        # ---------------------------------------------------------------------

        # HTTP_HOST
        http_host = (
            config.http_host or  # manually specified: top priority. Otherwise:
            self._get_first(environ, self.vars_host, keys_to_keep)
        )
        if http_host:
            environ[WsgiEnvVar.HTTP_HOST] = http_host

        # REMOTE_ADDR
        remote_addr = (
            config.remote_addr or
            self._get_first(environ, self.vars_addr, keys_to_keep,
                            as_remote_addr=True)
        )
        if remote_addr:
            environ[WsgiEnvVar.REMOTE_ADDR] = remote_addr

        # SCRIPT_NAME, PATH_INFO
        script_name = (
            config.script_name or
            self._get_first(environ, self.vars_script, keys_to_keep)
        )
        if script_name:
            environ[WsgiEnvVar.SCRIPT_NAME] = script_name
            path_info = environ[WsgiEnvVar.PATH_INFO]
            if config.rewrite_path_info and path_info.startswith(script_name):
                newpath = path_info[len(script_name):]
                if not newpath:  # e.g. trailing slash omitted from incoming path  # noqa
                    newpath = "/"
                environ[WsgiEnvVar.PATH_INFO] = newpath

        # SERVER_NAME
        server_name = (
            config.server_name or
            self._get_first(environ, self.vars_server, keys_to_keep)
        )
        if server_name:
            environ[WsgiEnvVar.SERVER_NAME] = server_name

        # SERVER_PORT
        server_port = (
            config.server_port or
            self._get_first(environ, self.vars_port, keys_to_keep)
        )
        if server_port:
            environ[WsgiEnvVar.SERVER_PORT] = server_port

        # wsgi.url_scheme
        url_scheme = (
            config.url_scheme or  # manually specified: top priority. Otherwise:
            self._get_first(environ, self.vars_scheme_a, keys_to_keep) or
            self._proto_if_one_true(environ, self.vars_scheme_b, keys_to_keep)
        )
        if url_scheme:
            url_scheme = url_scheme.lower()
            environ[WsgiEnvVar.WSGI_URL_SCHEME] = url_scheme

        # ---------------------------------------------------------------------

        # As per mod_wsgi, we delete unused and untrusted keys.
        delete_keys(environ,
                    keys_to_delete=self.ALL_CANDIDATES,
                    keys_to_keep=keys_to_keep)
        if self.debug:
            # noinspection PyUnboundLocalVariable
            changes = dict_diff(oldenv, environ)
            log.debug("Changes to WSGI environment: \n{}", pformat(changes))
        return self.app(environ, start_response)
