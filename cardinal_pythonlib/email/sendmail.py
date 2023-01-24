#!/usr/bin/env python
# cardinal_pythonlib/email/sendmail.py

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
from typing import List, NoReturn, Sequence, Tuple, Union

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Constants
# =============================================================================

CONTENT_TYPE_TEXT = "text/plain"
CONTENT_TYPE_HTML = "text/html"

ASCII = "ascii"
UTF8 = "utf8"

COMMA = ","
COMMASPACE = ", "

STANDARD_SMTP_PORT = 25
STANDARD_TLS_PORT = 587


# =============================================================================
# Make e-mail message
# =============================================================================


def make_email(
    from_addr: str,
    date: str = None,
    sender: str = "",
    reply_to: Union[str, List[str]] = "",
    to: Union[str, List[str]] = "",
    cc: Union[str, List[str]] = "",
    bcc: Union[str, List[str]] = "",
    subject: str = "",
    body: str = "",
    content_type: str = CONTENT_TYPE_TEXT,
    charset: str = UTF8,
    attachment_filenames: Sequence[str] = None,
    attachment_binaries: Sequence[bytes] = None,
    attachment_binary_filenames: Sequence[str] = None,
    verbose: bool = False,
) -> email.mime.multipart.MIMEMultipart:
    """
    Makes an e-mail message.

    Arguments that can be multiple e-mail addresses are (a) a single e-mail
    address as a string, or (b) a list of strings (each a single e-mail
    address), or (c) a comma-separated list of multiple e-mail addresses.

    Args:
        from_addr:
            name of the sender for the "From:" field
        date:
            e-mail date in RFC 2822 format, or ``None`` for "now"
        sender:
            name of the sender for the "Sender:" field
        reply_to:
            name of the sender for the "Reply-To:" field

        to:
            e-mail address(es) of the recipients for "To:" field
        cc:
            e-mail address(es) of the recipients for "Cc:" field
        bcc:
            e-mail address(es) of the recipients for "Bcc:" field

        subject:
            e-mail subject
        body:
            e-mail body
        content_type:
            MIME type for body content, default ``text/plain``
        charset:
            character set for body; default ``utf8``

        attachment_filenames:
            filenames of attachments to add
        attachment_binaries:
            binary objects to add as attachments
        attachment_binary_filenames:
            filenames corresponding to ``attachment_binaries``
        verbose: be verbose?

    Returns:
        a :class:`email.mime.multipart.MIMEMultipart`

    Raises:
        :exc:`AssertionError`, :exc:`ValueError`

    """

    def _csv_list_to_list(x: str) -> List[str]:
        stripped = [item.strip() for item in x.split(COMMA)]
        return [item for item in stripped if item]

    def _assert_nocomma(x: Union[str, List[str]]) -> None:
        if isinstance(x, str):
            x = [x]
        for _addr in x:
            assert (
                COMMA not in _addr
            ), f"Commas not allowed in e-mail addresses: {_addr!r}"

    # -------------------------------------------------------------------------
    # Arguments
    # -------------------------------------------------------------------------
    if not date:
        date = email.utils.formatdate(localtime=True)
    assert isinstance(from_addr, str), (
        f"'From:' can only be a single address "
        f"(for Python sendmail, not RFC 2822); was {from_addr!r}"
    )
    _assert_nocomma(from_addr)
    assert isinstance(
        sender, str
    ), f"'Sender:' can only be a single address; was {sender!r}"
    _assert_nocomma(sender)
    if isinstance(reply_to, str):
        reply_to = [reply_to] if reply_to else []  # type: List[str]
    _assert_nocomma(reply_to)
    if isinstance(to, str):
        to = _csv_list_to_list(to)
    if isinstance(cc, str):
        cc = _csv_list_to_list(cc)
    if isinstance(bcc, str):
        bcc = _csv_list_to_list(bcc)
    assert to or cc or bcc, "No recipients (must have some of: To, Cc, Bcc)"
    _assert_nocomma(to)
    _assert_nocomma(cc)
    _assert_nocomma(bcc)
    attachment_filenames = attachment_filenames or []  # type: List[str]
    assert all(
        attachment_filenames
    ), f"Missing attachment filenames: {attachment_filenames!r}"
    attachment_binaries = attachment_binaries or []  # type: List[bytes]
    attachment_binary_filenames = (
        attachment_binary_filenames or []
    )  # type: List[str]  # noqa
    assert len(attachment_binaries) == len(attachment_binary_filenames), (
        "If you specify attachment_binaries or attachment_binary_filenames, "
        "they must be iterables of the same length."
    )
    assert all(attachment_binary_filenames), (
        f"Missing filenames for attached binaries: "
        f"{attachment_binary_filenames!r}"
    )

    # -------------------------------------------------------------------------
    # Make message
    # -------------------------------------------------------------------------
    msg = email.mime.multipart.MIMEMultipart()

    # Headers: mandatory
    msg["From"] = from_addr
    msg["Date"] = date
    msg["Subject"] = subject

    # Headers: optional
    if sender:
        msg["Sender"] = sender  # Single only, not a list
    if reply_to:
        msg["Reply-To"] = COMMASPACE.join(reply_to)
    if to:
        msg["To"] = COMMASPACE.join(to)
    if cc:
        msg["Cc"] = COMMASPACE.join(cc)
    if bcc:
        msg["Bcc"] = COMMASPACE.join(bcc)

    # Body
    if content_type == CONTENT_TYPE_TEXT:
        msgbody = email.mime.text.MIMEText(body, "plain", charset)
    elif content_type == CONTENT_TYPE_HTML:
        msgbody = email.mime.text.MIMEText(body, "html", charset)
    else:
        raise ValueError("unknown content_type")
    msg.attach(msgbody)

    # Attachments
    # noinspection PyPep8,PyBroadException
    try:
        if attachment_filenames:
            # -----------------------------------------------------------------
            # Attach things by filename
            # -----------------------------------------------------------------
            if verbose:
                log.debug("attachment_filenames: {}", attachment_filenames)
            # noinspection PyTypeChecker
            for f in attachment_filenames:
                part = email.mime.base.MIMEBase("application", "octet-stream")
                part.set_payload(open(f, "rb").read())
                email.encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    'attachment; filename="%s"' % os.path.basename(f),
                )
                msg.attach(part)
        if attachment_binaries:
            # -----------------------------------------------------------------
            # Binary attachments, which have a notional filename
            # -----------------------------------------------------------------
            if verbose:
                log.debug(
                    "attachment_binary_filenames: {}",
                    attachment_binary_filenames,
                )
            for i in range(len(attachment_binaries)):
                blob = attachment_binaries[i]
                filename = attachment_binary_filenames[i]
                part = email.mime.base.MIMEBase("application", "octet-stream")
                part.set_payload(blob)
                email.encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    'attachment; filename="%s"' % filename,
                )
                msg.attach(part)
    except Exception as e:
        raise ValueError(f"send_email: Failed to attach files: {e}")

    return msg


# =============================================================================
# Send message
# =============================================================================


def send_msg(
    from_addr: str,
    to_addrs: Union[str, List[str]],
    host: str,
    user: str,
    password: str,
    port: int = None,
    use_tls: bool = True,
    msg: email.mime.multipart.MIMEMultipart = None,
    msg_string: str = None,
) -> None:
    """
    Sends a pre-built e-mail message.

    Args:
        from_addr: e-mail address for 'From:' field
        to_addrs: address or list of addresses to transmit to

        host: mail server host
        user: username on mail server
        password: password for username on mail server
        port: port to use, or ``None`` for protocol default
        use_tls: use TLS, rather than plain SMTP?

        msg: a :class:`email.mime.multipart.MIMEMultipart`
        msg_string: alternative: specify the message as a raw string

    Raises:
        :exc:`RuntimeError`

    See also:

    - https://tools.ietf.org/html/rfc3207

    """
    assert bool(msg) != bool(msg_string), "Specify either msg or msg_string"
    # Connect
    try:
        session = smtplib.SMTP(host, port)
    except OSError as e:
        # https://bugs.python.org/issue2118
        # Not all errors from smtplib are raised as SMTPException
        # e.g. ConnectionRefusedError when creating the socket
        # SMTPException is a subclass of OSError since 3.4
        raise RuntimeError(
            f"send_msg: Failed to connect to host {host}, port {port}: {e}"
        )
    try:
        session.ehlo()
    except smtplib.SMTPException as e:
        raise RuntimeError(f"send_msg: Failed to issue EHLO: {e}")

    if use_tls:
        try:
            session.starttls()
            session.ehlo()
        except smtplib.SMTPException as e:
            raise RuntimeError(f"send_msg: Failed to initiate TLS: {e}")

    # Log in
    if user:
        try:
            session.login(user, password)
        except smtplib.SMTPException as e:
            raise RuntimeError(
                f"send_msg: Failed to login as user {user}: {e}"
            )
    else:
        log.debug("Not using SMTP AUTH; no user specified")
        # For systems with... lax... security requirements

    # Send
    try:
        session.sendmail(from_addr, to_addrs, msg.as_string())
    except smtplib.SMTPException as e:
        raise RuntimeError(f"send_msg: Failed to send e-mail: {e}")

    # Log out
    session.quit()


# =============================================================================
# Send e-mail
# =============================================================================


def send_email(
    from_addr: str,
    host: str,
    user: str,
    password: str,
    port: int = None,
    use_tls: bool = True,
    date: str = None,
    sender: str = "",
    reply_to: Union[str, List[str]] = "",
    to: Union[str, List[str]] = "",
    cc: Union[str, List[str]] = "",
    bcc: Union[str, List[str]] = "",
    subject: str = "",
    body: str = "",
    content_type: str = CONTENT_TYPE_TEXT,
    charset: str = UTF8,
    attachment_filenames: Sequence[str] = None,
    attachment_binaries: Sequence[bytes] = None,
    attachment_binary_filenames: Sequence[str] = None,
    verbose: bool = False,
) -> Tuple[bool, str]:
    """
    Sends an e-mail in text/html format using SMTP via TLS.

    Args:
        host:
            mail server host
        user:
            username on mail server
        password:
            password for username on mail server
        port:
            port to use, or ``None`` for protocol default
        use_tls:
            use TLS, rather than plain SMTP?

        date:
            e-mail date in RFC 2822 format, or ``None`` for "now"

        from_addr:
            name of the sender for the "From:" field
        sender:
            name of the sender for the "Sender:" field
        reply_to:
            name of the sender for the "Reply-To:" field

        to:
            e-mail address(es) of the recipients for "To:" field
        cc:
            e-mail address(es) of the recipients for "Cc:" field
        bcc:
            e-mail address(es) of the recipients for "Bcc:" field

        subject:
            e-mail subject
        body:
            e-mail body
        content_type:
            MIME type for body content, default ``text/plain``
        charset:
            character set for body; default ``utf8``

        attachment_filenames:
            filenames of attachments to add
        attachment_binaries:
            binary objects to add as attachments
        attachment_binary_filenames:
            filenames corresponding to ``attachment_binaries``
        verbose:
            be verbose?

    Returns:
         tuple: ``(success, error_or_success_message)``

    See

    - https://tools.ietf.org/html/rfc2822
    - https://tools.ietf.org/html/rfc5322
    - https://segfault.in/2010/12/sending-gmail-from-python/
    - https://stackoverflow.com/questions/64505
    - https://stackoverflow.com/questions/3362600

    Re security:

    - TLS supersedes SSL:
      https://en.wikipedia.org/wiki/Transport_Layer_Security

    - https://en.wikipedia.org/wiki/Email_encryption

    - SMTP connections on ports 25 and 587 are commonly secured via TLS using
      the ``STARTTLS`` command:
      https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol

    - https://tools.ietf.org/html/rfc8314

    - "STARTTLS on port 587" is one common method. Django refers to this as
      "explicit TLS" (its ``E_MAIL_USE_TLS`` setting; see
      https://docs.djangoproject.com/en/2.1/ref/settings/#std:setting-EMAIL_USE_TLS).

    - Port 465 is also used for "implicit TLS" (3.3 in
      https://tools.ietf.org/html/rfc8314). Django refers to this as "implicit
      TLS" too, or SSL; see its ``EMAIL_USE_SSL`` setting at
      https://docs.djangoproject.com/en/2.1/ref/settings/#email-use-ssl). We
      don't support that here.

    """  # noqa
    if isinstance(to, str):
        to = [to]
    if isinstance(cc, str):
        cc = [cc]
    if isinstance(bcc, str):
        bcc = [bcc]

    # -------------------------------------------------------------------------
    # Make it
    # -------------------------------------------------------------------------
    try:
        msg = make_email(
            from_addr=from_addr,
            date=date,
            sender=sender,
            reply_to=reply_to,
            to=to,
            cc=cc,
            bcc=bcc,
            subject=subject,
            body=body,
            content_type=content_type,
            charset=charset,
            attachment_filenames=attachment_filenames,
            attachment_binaries=attachment_binaries,
            attachment_binary_filenames=attachment_binary_filenames,
            verbose=verbose,
        )
    except (AssertionError, ValueError) as e:
        errmsg = str(e)
        log.error("{}", errmsg)
        return False, errmsg

    # -------------------------------------------------------------------------
    # Send it
    # -------------------------------------------------------------------------

    to_addrs = to + cc + bcc
    try:
        send_msg(
            msg=msg,
            from_addr=from_addr,
            to_addrs=to_addrs,
            host=host,
            user=user,
            password=password,
            port=port,
            use_tls=use_tls,
        )
    except RuntimeError as e:
        errmsg = str(e)
        log.error("{}", e)
        return False, errmsg

    return True, "Success"


# =============================================================================
# Misc
# =============================================================================

_SIMPLE_EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")


def is_email_valid(email_: str) -> bool:
    """
    Performs some basic checks that a string appears to be an e-mail address.

    See
    https://stackoverflow.com/questions/8022530/how-to-check-for-valid-email-address.
    """  # noqa
    # Very basic checks!
    if not email_:
        return False
    if _SIMPLE_EMAIL_REGEX.match(email_) is None:
        return False
    # The other things that can get through:
    # Exclude e.g. two @ symbols
    if email_.count("@") != 1:
        return False
    # Commas are not allowed
    if email_.count(",") != 0:
        return False
    # Can't end in a full stop:
    if email_.endswith("."):
        return False
    return True


def get_email_domain(email_: str) -> str:
    """
    Returns the domain part of an e-mail address.
    """
    return email_.split("@")[1]


# =============================================================================
# Parse command line
# =============================================================================


def main() -> NoReturn:
    """
    Command-line processor. See ``--help`` for details.
    """
    logging.basicConfig()
    log.setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser(
        description="Send an e-mail from the command line."
    )
    parser.add_argument(
        "sender", action="store", help="Sender's e-mail address"
    )
    parser.add_argument("host", action="store", help="SMTP server hostname")
    parser.add_argument("user", action="store", help="SMTP username")
    parser.add_argument("password", action="store", help="SMTP password")
    parser.add_argument(
        "recipient", action="append", help="Recipient e-mail address(es)"
    )
    parser.add_argument("subject", action="store", help="Message subject")
    parser.add_argument("body", action="store", help="Message body")
    parser.add_argument("--attach", nargs="*", help="Filename(s) to attach")
    parser.add_argument(
        "--tls", action="store_false", help="Use TLS connection security"
    )
    parser.add_argument("--verbose", action="store_true", help="Be verbose")
    parser.add_argument("-h --help", action="help", help="Prints this help")
    args = parser.parse_args()
    (result, msg) = send_email(
        from_addr=args.sender,
        to=args.recipient,
        subject=args.subject,
        body=args.body,
        host=args.host,
        user=args.user,
        password=args.password,
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


if __name__ == "__main__":
    main()
