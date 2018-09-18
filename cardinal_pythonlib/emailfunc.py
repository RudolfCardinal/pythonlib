#!/usr/bin/env python
# cardinal_pythonlib/mail.py

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

**Sends e-mails from the command line.**

"""

import argparse
import email.encoders
import email.mime.base
import email.mime.text
import email.mime.multipart
import email.header
import email.utils
import logging
import os
import re
import smtplib
import sys
from typing import Iterable, List, Tuple, Union

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

STANDARD_SMTP_PORT = 25
STANDARD_TLS_PORT = 587


# =============================================================================
# Send e-mail
# =============================================================================

def send_email(sender: str,
               recipient: Union[str, List[str]],
               subject: str,
               body: str,
               host: str,
               user: str,
               password: str,
               port: int = None,
               use_tls: bool = True,
               content_type: str = "text/plain",
               attachment_filenames: Iterable[str] = None,
               attachment_binaries: Iterable[bytes] = None,
               attachment_binary_filenames: Iterable[str] = None,
               charset: str = "utf8",
               verbose: bool = False) -> Tuple[bool, str]:
    """
    Sends an e-mail in text/html format using SMTP via TLS.

    Args:
        sender: name of the sender
        recipient: e-mail address(es) of the recipients
        subject: e-mail subject
        body: e-mail body
        host: mail server host
        user: username on mail server
        password: password for username on mail server
        port: port to use, or ``None`` for protocol default
        use_tls: use TLS, rather than plain SMTP?
        content_type: MIME type for content, default ``text/plain``
        attachment_filenames: filenames of attachments to add
        attachment_binaries: binary objects to add as attachments
        attachment_binary_filenames: filenames corresponding to
            ``attachment_binaries``
        charset: character set, default ``utf8``
        verbose: be verbose?

    Returns:
         tuple: ``(success, error_or_success_message)``

    """
    # http://segfault.in/2010/12/sending-gmail-from-python/
    # http://stackoverflow.com/questions/64505
    # http://stackoverflow.com/questions/3362600
    attachment_filenames = attachment_filenames or []
    attachment_binaries = attachment_binaries or []
    attachment_binary_filenames = attachment_binary_filenames or []
    if port is None:
        port = STANDARD_TLS_PORT if use_tls else STANDARD_SMTP_PORT
    if content_type == "text/plain":
        msgbody = email.mime.text.MIMEText(body, "plain", charset)
    elif content_type == "text/html":
        msgbody = email.mime.text.MIMEText(body, "html", charset)
    else:
        errmsg = "send_email: unknown content_type"
        log.error(errmsg)
        return False, errmsg

    # Make message
    msg = email.mime.multipart.MIMEMultipart()
    msg["From"] = sender
    if type(recipient) == list:
        msg["To"] = ", ".join(recipient)
    else:
        msg["To"] = recipient
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Subject"] = subject
    msg.attach(msgbody)

    # Attachments
    # noinspection PyPep8,PyBroadException
    try:
        if attachment_filenames is not None:
            if verbose:
                log.debug("attachment_filenames: {}".format(
                    attachment_filenames))
            # noinspection PyTypeChecker
            for f in attachment_filenames:
                part = email.mime.base.MIMEBase("application", "octet-stream")
                part.set_payload(open(f, "rb").read())
                email.encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    'attachment; filename="%s"' % os.path.basename(f)
                )
                msg.attach(part)
        if (attachment_binaries is not None and
                attachment_binary_filenames is not None and
                (
                    len(attachment_binaries) ==
                    len(attachment_binary_filenames)
                )):
            if verbose:
                log.debug("attachment_binary_filenames: {}".format(
                    attachment_binary_filenames))
            for i in range(len(attachment_binaries)):
                blob = attachment_binaries[i]
                filename = attachment_binary_filenames[i]
                part = email.mime.base.MIMEBase("application", "octet-stream")
                part.set_payload(blob)
                email.encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    'attachment; filename="%s"' % filename)
                msg.attach(part)
    except:
        errmsg = "send_email: Failed to attach files"
        log.error(errmsg)
        return False, errmsg

    # Connect
    try:
        session = smtplib.SMTP(host, port)
    except smtplib.SMTPException:
        errmsg = "send_email: Failed to connect to host {}, port {}".format(
            host, port)
        log.error(errmsg)
        return False, errmsg
    try:
        session.ehlo()
        session.starttls()
        session.ehlo()
    except smtplib.SMTPException:
        errmsg = "send_email: Failed to initiate TLS"
        log.error(errmsg)
        return False, errmsg

    # Log in
    try:
        session.login(user, password)
    except smtplib.SMTPException:
        errmsg = "send_email: Failed to login as user {}".format(user)
        log.error(errmsg)
        return False, errmsg

    # Send
    try:
        session.sendmail(sender, recipient, msg.as_string())
    except smtplib.SMTPException as e:
        errmsg = "send_email: Failed to send e-mail: exception: " + str(e)
        log.error(errmsg)
        return False, errmsg

    # Log out
    session.quit()

    return True, "Success"


# =============================================================================
# Misc
# =============================================================================

_SIMPLE_EMAIL_REGEX = re.compile("[^@]+@[^@]+\.[^@]+")


def is_email_valid(email_: str) -> bool:
    """
    Performs a very basic check that a string appears to be an e-mail address.
    """
    # Very basic checks!
    return _SIMPLE_EMAIL_REGEX.match(email_) is not None


def get_email_domain(email_: str) -> str:
    """
    Returns the domain part of an e-mail address.
    """
    return email_.split("@")[1]


# =============================================================================
# Parse command line
# =============================================================================

def main() -> None:
    """
    Command-line processor. See ``--help`` for details.
    """
    logging.basicConfig()
    log.setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser(
        description="Send an e-mail from the command line.")
    parser.add_argument("sender", action="store",
                        help="Sender's e-mail address")
    parser.add_argument("host", action="store",
                        help="SMTP server hostname")
    parser.add_argument("user", action="store",
                        help="SMTP username")
    parser.add_argument("password", action="store",
                        help="SMTP password")
    parser.add_argument("recipient", action="append",
                        help="Recipient e-mail address(es)")
    parser.add_argument("subject", action="store",
                        help="Message subject")
    parser.add_argument("body", action="store",
                        help="Message body")
    parser.add_argument("--attach", nargs="*",
                        help="Filename(s) to attach")
    parser.add_argument("--tls", action="store_false",
                        help="Use TLS connection security")
    parser.add_argument("--verbose", action="store_true",
                        help="Be verbose")
    parser.add_argument("-h --help", action="help",
                        help="Prints this help")
    args = parser.parse_args()
    (result, msg) = send_email(
        args.sender,
        args.recipient,
        args.subject,
        args.body,
        args.host,
        args.user,
        args.password,
        use_tls=args.tls,
        attachment_filenames=args.attach,
        verbose=args.verbose,
    )
    if result:
        log.info("Success")
    else:
        log.info("Failure")
        # log.error(msg)
    sys.exit(0 if result else 1)


if __name__ == '__main__':
    main()
