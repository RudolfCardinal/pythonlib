#!/usr/bin/env python
# cardinal_pythonlib/email/mailboxpurge.py

"""
Remove all binary attachments from email messages

This is a standard UNIX filter; it reads a message or mailbox from standard
input, and outputs it again on standard output, with all binary attachments
removed (with message/external-body).

Written by Frédéric Brière <fbriere@fbriere.net>.  Copy at will.
Adapted from <https://code.activestate.com/recipes/576553/>, originally
written by Romain Dartigues.

From https://gist.github.com/fbriere/e86584a807449e3128c0

Then rewritten a fair bit, Rudolf Cardinal, 9 Oct 2018

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

"""

import argparse
from email.message import Message
import logging
import mailbox
import os
import time

from cardinal_pythonlib.logs import (
    get_brace_style_log_with_null_handler,
    main_only_quicksetup_rootlogger,
)
from cardinal_pythonlib.sizeformatter import bytes2human

log = get_brace_style_log_with_null_handler(__name__)


def gut_message(message: Message) -> Message:
    """
    Remove body from a message, and wrap in a message/external-body.
    """
    wrapper = Message()
    wrapper.add_header(
        "Content-Type",
        "message/external-body",
        access_type="x-spam-deleted",
        expiration=time.strftime("%a, %d %b %Y %H:%M:%S %z"),
        size=str(len(message.get_payload())),
    )

    message.set_payload("")
    wrapper.set_payload([message])

    return wrapper


def message_is_binary(message: Message) -> bool:
    """
    Determine if a non-multipart message is of binary type.
    """
    return message.get_content_maintype() not in ("text", "message")


def clean_message(message: Message, topmost: bool = False) -> Message:
    """
    Clean a message of all its binary parts.

    This guts all binary attachments, and returns the message itself for
    convenience.

    """
    if message.is_multipart():
        # Don't recurse in already-deleted attachments
        if message.get_content_type() != "message/external-body":
            parts = message.get_payload()
            parts[:] = map(clean_message, parts)
    elif message_is_binary(message):
        # Don't gut if this is the topmost message
        if not topmost:
            message = gut_message(message)

    return message


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a mailbox file from stdin to stdout, "
        "removing any attachments",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=str, help="Filename for input")
    parser.add_argument("output", type=str, help="Filename for output")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Be verbose"
    )
    parser.add_argument(
        "--report", type=int, default=100, help="Report every n messages"
    )
    args = parser.parse_args()
    main_only_quicksetup_rootlogger(
        level=logging.DEBUG if args.verbose else logging.INFO
    )

    if os.path.exists(args.output):
        errmsg = f"Output file exists: {args.output}"
        log.critical(errmsg)
        raise ValueError(errmsg)
    log.info(
        "Opening input file: {filename} ({size})",
        filename=args.input,
        size=bytes2human(os.path.getsize(args.input)),
    )
    input_box = mailbox.mbox(args.input, create=False)
    log.info("Opening output file: {} (new file)", args.output)
    output_box = mailbox.mbox(args.output, create=True)

    log.info("Processing messages...")
    msg_count = 0
    for message in input_box.itervalues():
        msg_count += 1
        if msg_count % args.report == 0:
            log.debug("Processing message {}", msg_count)
        processed_msg = clean_message(message, topmost=True)
        output_box.add(processed_msg)
    log.info("Done; processed {} messages.", msg_count)
    log.info("Output size: {}", bytes2human(os.path.getsize(args.output)))


if __name__ == "__main__":
    main()
