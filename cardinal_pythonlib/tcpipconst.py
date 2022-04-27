#!/usr/bin/env python
# cardinal_pythonlib/tcpipconst.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

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

**Constants for use with TCP/IP.**

"""


# =============================================================================
# Common TCP/IP ports
# =============================================================================


class Ports(object):
    """
    Common TCP/UDP ports.

    - https://en.wikipedia.org/wiki/Port_(computer_networking)
    - https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers
    """

    # -------------------------------------------------------------------------
    # System (well-known) ports are in the range 0-1023.
    # -------------------------------------------------------------------------

    FTP_DATA = 20  # not for initiating connections
    FTP_CONTROL = 21  # for initiating connections
    FTP = FTP_CONTROL
    SSH = 22
    SFTP = SSH  # SFTP is FTP over SSH
    TELNET = 23
    HTTP = 80
    NTP = 123
    HTTPS = 443

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # E-mail is a special mess:
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # As of RFC8314 (2018), the recommendations are:
    #
    # - Connect via "implicit TLS" ports (always encrypted), rather than
    #   connecting to the "cleartext" port and negotiating TLS using the
    #   "STARTTLS" command.
    #
    #   - I think that means: use 465 for SMTP, 993 for IMAP, 995 for POP3.
    #
    # However, 587 was always the official e-mail submission port. And RFC8134
    # is a standards-track document, not an accepted standard
    # (https://www.rfc-editor.org/info/rfc8314). Currently RFC8314 says that
    # servers SHOULD support both 587 and 465.
    #
    # Older sources will say that 587 is preferred for SMTP. See
    # https://serverfault.com/questions/1064955/why-is-port-587-preferred-over-port-465-in-smtp  # noqa

    SMTP = 25  # its formal IANA name;
    # ... https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml?search=25  # noqa
    SMTP_UNENCRYPTED = 25  # https://datatracker.ietf.org/doc/html/rfc5321
    SMTP_MTA = SMTP
    # ... MTA = message transfer agent = for server-to-server transmission
    # ... receives from an MUA (mail user agent = e-mail client)

    POP3 = 110  # formal name
    POP3_UNENCRYPTED = POP3

    IMAP = 143  # formal name
    IMAP_UNENCRYPTED = IMAP

    SUBMISSIONS = 465  # formal name; message submission over TLS
    # ... "submission-s[ecure]", not plural of submission.
    SMTPS = SUBMISSIONS
    # ... https://datatracker.ietf.org/doc/html/rfc8314
    # ... https://stackoverflow.com/questions/15796530/what-is-the-difference-between-ports-465-and-587  # noqa
    # ... requires negotiation of TLS/SSL at connection setup
    # Was initially intended for another purpose (URL Rendezvous Directory for
    # SSM), but was co-opted for e-mail and formalized by RFC8314.
    SMTP_PREFERRED = SUBMISSIONS
    # ... this is the best for client-to-server transmission (per RFC8314)

    SUBMISSION = 587  # formal name; message submission
    SMTP_MSA = SUBMISSION
    # ... MSA = message submission agent = client-to-server
    # ... can
    # ... https://datatracker.ietf.org/doc/html/rfc8314
    # ... https://stackoverflow.com/questions/15796530/what-is-the-difference-between-ports-465-and-587  # noqa
    # ... requires SMTP AUTH (authentication);
    #     https://en.wikipedia.org/wiki/SMTP_Authentication
    # ... uses STARTTLS if one chooses to negotiate TLS

    IMAPS = 993  # formal name; IMAP over TLS
    IMAP_ENCRYPTED = IMAPS

    POP3S = 995  # formal name; POP3 over TLS
    POP3_ENCRYPTED = POP3S

    # -------------------------------------------------------------------------
    # Registered ports are in the range 1024 to 49151.
    # -------------------------------------------------------------------------

    MS_SQL_S = 1433  # formal name; a database
    MICROSOFT_SQL_SERVER = MS_SQL_S  # a database
    HL7 = 2575  # formal name; HL7 messaging
    HL7_MLLP = HL7  # HL7 MLLP = Minimum Lower Layer Protocol
    MYSQL = 3306  # a database
    WHISKER = 3233  # a behavioural research control system
    POSTGRESQL = 5432  # a database
    AMQP = 5672  # Advanced Message Queuing Protocol

    # -------------------------------------------------------------------------
    # Dynamic ports are in the range 49152 to 65535.
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Some non-standard ports:
    # -------------------------------------------------------------------------

    FLOWER_NONSTANDARD = 5555
    # ... default internal port for Flower, https://flower.readthedocs.io/
    ALTERNATIVE_HTTP_NONSTANDARD = 8000
    RABBITMQ_ADMIN_NONSTANDARD = 15672
    # ... default internal port for RabbitMQ admin interface;
    # https://www.rabbitmq.com/


class UriSchemes:
    """
    Common URI schemes.
    See https://en.wikipedia.org/wiki/List_of_URI_schemes.
    """

    FTP = "ftp"
    HTTP = "http"
    HTTPS = "https"
    IMAP = "imap"
    MAILTO = "mailto"
    SFTP = "sftp"
    SMS = "sms"
    SSH = "ssh"
    TEL = "tel"  # telephone
    TELNET = "telnet"
