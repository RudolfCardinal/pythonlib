#!/usr/bin/env python
# cardinal_pythonlib/bulk_email/main.py

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

Command-line entry point for the simple bulk e-mail tool.

"""

# =============================================================================
# Imports
# =============================================================================

import argparse
from copy import deepcopy
from datetime import datetime
from email.utils import format_datetime as format_email_datetime
import logging
import os
import sys
from time import sleep
from typing import List, Optional, Set

# noinspection PyProtectedMember
from sqlalchemy.engine import create_engine, Engine
from sqlalchemy.orm.session import Session

from cardinal_pythonlib.bulk_email.constants import (
    DB_URL_ENVVAR,
    DEFAULT_TIME_BETWEEN_EMAILS_S,
    PASSWORD_OBSCURING_STRING,
)
from cardinal_pythonlib.bulk_email.models import (
    Base,
    Config,
    Content,
    Job,
    Recipient,
    SendAttempt,
)
from cardinal_pythonlib.email.sendmail import (
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_TEXT,
    is_email_valid,
    send_email,
    STANDARD_SMTP_PORT,
    STANDARD_TLS_PORT,
    UTF8,
)
from cardinal_pythonlib.file_io import gen_lines_without_comments
from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger
from cardinal_pythonlib.sqlalchemy.session import get_safe_url_from_engine
from cardinal_pythonlib.sysops import EXIT_FAILURE, EXIT_SUCCESS

log = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================


class Command:
    """
    Commands to this tool.
    """

    ADD = "add"
    CLEAR = "clear"
    CONFIGURE = "configure"
    CREATE_DB = "create_database_destroying_existing_data"
    INFO = "info"
    WORK = "work"


# =============================================================================
# Create database
# =============================================================================


def create_db(engine: Engine) -> None:
    """
    Creates the database.
    """
    log.info("Dropping existing tables...")
    Base.metadata.drop_all(engine)

    log.info("Creating tables...")
    Base.metadata.create_all(engine)

    log.info("Database created.")


# =============================================================================
# Configure server settings
# =============================================================================


def configure(
    session: Session,
    host: str,
    port: int,
    use_tls: bool,
    username: str,
    password: str,
    time_between_emails: float,
) -> None:
    """
    Updates the configuration from command-line parameters.
    """
    cfg = Config.get_or_create_config(session)

    cfg.host = host
    cfg.port = port
    cfg.use_tls = use_tls
    cfg.username = username
    cfg.password = password
    cfg.time_between_emails = time_between_emails

    session.commit()
    log.info("Configuration updated.")


# =============================================================================
# Add a job
# =============================================================================


def add_job(
    session: Session,
    recipients_filename: str,
    from_addr: str,  # avoid clash with "from" keyword
    reply_to_addr: str,
    subject: str,
    content_html_filename: Optional[str],
    content_text_filename: Optional[str],
    charset: str,
    timestamp_at_creation: bool,
) -> None:
    """
    Adds an e-mail sending job -- contents and recipients.
    """
    # -------------------------------------------------------------------------
    # Recipients
    # -------------------------------------------------------------------------

    log.info(f"Reading recipients from: {recipients_filename}")
    recipient_addresses = set()  # type: Set[str]
    recipients_failed = False
    for recipient_addr in gen_lines_without_comments(recipients_filename):
        if not is_email_valid(recipient_addr):
            log.error(f"Bad recipient e-mail: {recipient_addr}")
            recipients_failed = True
        else:
            recipient_addresses.add(recipient_addr)
    if recipients_failed:
        raise ValueError("Errors in recipient addresses")

    recipients = []  # type: List[Recipient]
    for recipient_addr in sorted(recipient_addresses):
        recipient = Recipient.fetch_or_add(recipient_addr, session)
        session.add(recipient)
        recipients.append(recipient)
    log.info(f"Read {len(recipients)} recipients.")

    # -------------------------------------------------------------------------
    # Contents
    # -------------------------------------------------------------------------

    log.info("Creating template...")
    if timestamp_at_creation:
        email_datetime = datetime.now()
    else:
        email_datetime = None  # timestamp at sending

    assert bool(content_text_filename) != bool(content_html_filename)
    if content_text_filename:
        filename = content_text_filename
        content_type = CONTENT_TYPE_TEXT
    else:
        filename = content_html_filename
        content_type = CONTENT_TYPE_HTML
    with open(filename) as f:
        body = f.read()

    content = Content(
        from_addr=from_addr,
        reply_to_addr=reply_to_addr,
        email_datetime=email_datetime,
        subject=subject,
        body=body,
        content_type=content_type,
        charset=charset,
    )
    session.add(content)
    log.info("... created.")

    # -------------------------------------------------------------------------
    # Jobs
    # -------------------------------------------------------------------------

    log.info("Adding jobs...")
    for recipient in recipients:
        job = Job(recipient=recipient, content=content)
        session.add(job)
    log.info("... done.")


# =============================================================================
# Send pending emails
# =============================================================================


def work(session: Session, stop_on_error: bool) -> None:
    """
    Processes outstanding jobs until there are no more.
    """
    log.info("Processing pending jobs...")
    config = Config.get_current_config(session)
    sleep_time_s = config.time_between_emails
    for i, job in enumerate(Job.gen_jobs_to_be_done(session)):
        if i != 0:
            log.info(f"Sleeping for {sleep_time_s} s...")
            sleep(sleep_time_s)
        content = job.content
        recipient = job.recipient
        log.info(f"Sending to: {recipient.email}")
        now = datetime.now()
        if content.email_datetime:
            email_datetime = format_email_datetime(content.email_datetime)
        else:
            email_datetime = None  # "now"
        success, details = send_email(
            from_addr=content.from_addr,
            host=config.host,
            user=config.username,
            password=config.password,
            port=config.port,
            use_tls=config.use_tls,
            date=email_datetime,  # may be None for "now"
            sender="",
            reply_to=content.reply_to_addr,
            to=recipient.email,
            cc="",
            bcc="",
            subject=content.subject,
            body=content.body,
            content_type=content.content_type,
            charset=content.charset,
            attachment_filenames=None,
            attachment_binaries=None,
            attachment_binary_filenames=None,
            verbose=False,
        )
        attempt = SendAttempt(
            job=job,
            config=config,
            when_attempt=now,
            success=success,
            details=details,
        )
        session.add(attempt)
        if success:
            log.info("... success")
        else:
            log.error(f"... failed: {details}")
            if stop_on_error:
                log.error("Stopping because of errors.")
                return
    log.info("Done.")


# =============================================================================
# Show info
# =============================================================================


def info(session: Session) -> None:
    """
    Shows information about jobs, to stdout.
    """
    n_recipients = Recipient.n_recipients(session)
    n_content_templates = Content.n_templates(session)
    n_complete = Job.n_completed_jobs(session)
    n_pending = Job.n_pending_jobs(session)

    print(
        f"""Status:

Recipients: {n_recipients}
Content templates: {n_content_templates}
Jobs complete: {n_complete}
Jobs pending: {n_pending}
"""
    )


# =============================================================================
# Clear pending jobs
# =============================================================================


def clear_pending_jobs(session: Session) -> None:
    """
    Shows information about jobs, to stdout.
    """
    log.info("Deleting pending jobs...")
    Job.clear_pending_jobs(session)
    log.info("... done.")


# =============================================================================
# Command-line entry point.
# =============================================================================


def main() -> None:
    """
    Command-line entry point.
    """

    # -------------------------------------------------------------------------
    # Arguments
    # -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Simple bulk e-mail tool. All data are stored in a "
        "relational database (e.g. SQLite).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Top-level arguments
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help=f"Database URL, in SQLAlchemy format. If not specified, it will "
        f"be taken from the environment variable {DB_URL_ENVVAR}",
    )
    parser.add_argument("--echo", action="store_true", help="Echo all SQL")
    parser.add_argument("--verbose", action="store_true", help="Be verbose")

    # Subparsers
    # We don't use "set_defaults(func=somefunc)" because we want to have more
    # control prior to launching the subcommand.
    subparsers = parser.add_subparsers(
        help="Append '--help' to any command for further help.",
        dest="command",  # store name of chosen command here
    )
    subparsers.required = True

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Subcommand: create_database_destroying_existing_data
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    _ = subparsers.add_parser(
        Command.CREATE_DB,
        help="Set up the database structure. Beware: DESTROYS EXISTING DATA.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Subcommand: configure
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    parser_configure = subparsers.add_parser(
        Command.CONFIGURE,
        help="Configure the e-mailer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_configure.add_argument(
        "--host", type=str, required=True, help="Mail server (SMTP) hostname."
    )
    parser_configure.add_argument(
        "--port",
        type=str,
        default=STANDARD_TLS_PORT,
        help=f"Mail server TCP port (e.g. {STANDARD_SMTP_PORT} for plain "
        f"SMTP, {STANDARD_TLS_PORT} for TLS).",
    )
    # Requires Python 3.9:
    # action=argparse.BooleanOptionalAction,
    parser_configure.add_argument(
        "--tls",
        action="store_true",
        default=True,
        help="Use TLS? (Enabled by default.)",
    )
    parser_configure.add_argument(
        "--no-tls", dest="tls", action="store_false", help="Disable TLS?"
    )
    parser_configure.add_argument(
        "--username", type=str, required=True, help="Username on mail server."
    )
    parser_configure.add_argument(
        "--password",
        type=str,
        required=True,
        help="Password on mail server. (WILL BE STORED IN DATABASE.)",
    )
    parser_configure.add_argument(
        "--time_between_emails",
        type=float,
        default=DEFAULT_TIME_BETWEEN_EMAILS_S,
        help="Time (in seconds) between each e-mail to be sent. Your server "
        "may object if you send them too fast.",
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Subcommand: add
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    parser_add_job = subparsers.add_parser(
        Command.ADD,
        help="Adds a bulk e-mail job.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_add_job.add_argument(
        "--recipients_file",
        type=str,
        required=True,
        help="Name of a file containing one recipient e-mail address per line.",
    )
    parser_add_job.add_argument(
        "--from_addr", type=str, required=True, help="From address."
    )
    parser_add_job.add_argument(
        "--reply_to_addr", type=str, help="Reply-To address."
    )
    parser_add_job.add_argument(
        "--subject", type=str, required=True, help="E-mail subject."
    )
    contents_group = parser_add_job.add_mutually_exclusive_group(required=True)
    contents_group.add_argument(
        "--content_html_file", type=str, help="E-mail contents as HTML."
    )
    contents_group.add_argument(
        "--content_text_file", type=str, help="E-mail contents as plain text."
    )
    parser_add_job.add_argument(
        "--charset", type=str, default=UTF8, help="Encoding (character set)."
    )
    parser_add_job.add_argument(
        "--timestamp_at_creation",
        action="store_true",
        help="Set the e-mail's date/time to now, as it's created, rather than "
        "when each copy is sent (the default).",
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Subcommand: work
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    parser_work = subparsers.add_parser(
        Command.WORK,
        help="Does work that is pending.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_work.add_argument(
        "--stop_on_error",
        action="store_true",
        default=True,
        help="Stop if an error occurs. (The default.)",
    )
    parser_work.add_argument(
        "--continue_on_error",
        dest="stop_on_error",
        action="store_false",
        help="Continue if an error occors.",
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Subcommand: info
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    _ = subparsers.add_parser(
        Command.INFO,
        help="Shows information about the jobs (queued and done).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Subcommand: clear
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    _ = subparsers.add_parser(
        Command.CLEAR,
        help="Clear pending jobs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Parse arguments
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    main_only_quicksetup_rootlogger(
        level=logging.DEBUG if args.verbose else logging.INFO
    )
    if args.verbose:
        # Show arguments, but obscuring any password.
        safe_args = deepcopy(args)
        if hasattr(safe_args, "password"):
            safe_args.password = PASSWORD_OBSCURING_STRING
        log.debug(f"Arguments: {safe_args}")

    # -------------------------------------------------------------------------
    # Database (always required)
    # -------------------------------------------------------------------------
    db_url = args.db or os.environ.get(DB_URL_ENVVAR)
    if not db_url:
        log.critical(
            f"Must specify the database URL, either via '--db' or "
            f"via the environment variable {DB_URL_ENVVAR}"
        )
        sys.exit(EXIT_FAILURE)
    engine = create_engine(db_url, echo=args.echo)
    log.info(f"Using database: {get_safe_url_from_engine(engine)}")
    session = Session(engine)

    # -------------------------------------------------------------------------
    # Launch subcommand
    # -------------------------------------------------------------------------
    command = args.command

    if command == Command.CREATE_DB:
        create_db(engine)

    elif command == Command.CONFIGURE:
        configure(
            session=session,
            host=args.host,
            port=args.port,
            use_tls=args.tls,
            username=args.username,
            password=args.password,
            time_between_emails=args.time_between_emails,
        )

    elif command == Command.ADD:
        add_job(
            session=session,
            recipients_filename=args.recipients_file,
            from_addr=args.from_addr,
            reply_to_addr=args.reply_to_addr,
            subject=args.subject,
            content_html_filename=args.content_html_file,
            content_text_filename=args.content_text_file,
            charset=args.charset,
            timestamp_at_creation=args.timestamp_at_creation,
        )

    elif command == Command.WORK:
        work(session=session, stop_on_error=args.stop_on_error)

    elif command == Command.INFO:
        info(session)

    elif command == Command.CLEAR:
        clear_pending_jobs(session)

    else:
        raise ValueError(f"Unknown command: {command}")

    # -------------------------------------------------------------------------
    # Commit
    # -------------------------------------------------------------------------
    session.commit()

    # -------------------------------------------------------------------------
    # Done
    # -------------------------------------------------------------------------
    sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
