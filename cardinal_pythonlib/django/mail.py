#!/usr/bin/env python
# cardinal_pythonlib/django/mail.py

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

**E-mail backend for Django that fixes a TLS bug.**

"""

import logging
import smtplib
import ssl

from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.utils import DNS_NAME

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SmtpEmailBackendTls1(EmailBackend):
    """
    Overrides ``django.core.mail.backends.smtp.EmailBackend`` to require TLS
    v1.
    Use this if your existing TLS server gives the error:

    .. code-block:: none

        ssl.SSLEOFError: EOF occurred in violation of protocol (_ssl.c:600)

    ... which appears to be a manifestation of changes in Python's
    ``smtplib`` library, which relies on its ``ssl`` library, which relies on
    OpenSSL. Something here has changed and now some servers that only support
    TLS version 1.0 don't work. In these situations, the following code fails:

    .. code-block:: python

        import smtplib
        s = smtplib.SMTP(host, port)  # port typically 587
        print(s.help())  # so we know we're communicating
        s.ehlo()  # ditto
        s.starttls()  # fails with ssl.SSLEOFError as above

    and this works:

    .. code-block:: python

        import smtplib
        import ssl
        s = smtplib.SMTP(host, port)
        c = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        s.ehlo()
        s.starttls(context=c)  # works

    then to send a simple message:

    .. code-block:: python

        s.login(user, password)
        s.sendmail(sender, recipient, message)
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not self.use_tls:
            raise ValueError("This backend is specifically for TLS.")
            # self.use_ssl will be False, by the superclass's checks

    @staticmethod
    def _protocol():
        # noinspection PyUnresolvedReferences
        return ssl.PROTOCOL_TLSv1

    def open(self) -> bool:
        """
        Ensures we have a connection to the email server. Returns whether or
        not a new connection was required (True or False).
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            return False

        connection_params = {'local_hostname': DNS_NAME.get_fqdn()}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        try:
            self.connection = smtplib.SMTP(self.host, self.port,
                                           **connection_params)

            # TLS
            context = ssl.SSLContext(self._protocol())
            if self.ssl_certfile:
                context.load_cert_chain(certfile=self.ssl_certfile,
                                        keyfile=self.ssl_keyfile)
            self.connection.ehlo()
            self.connection.starttls(context=context)
            self.connection.ehlo()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
                log.debug("Successful SMTP connection/login")
            else:
                log.debug("Successful SMTP connection (without login)")
            return True
        except smtplib.SMTPException:
            log.debug("SMTP connection and/or login failed")
            if not self.fail_silently:
                raise
