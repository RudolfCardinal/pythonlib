#!/usr/bin/env python
# cardinal_pythonlib/tools/backup_mysql_database.py

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

**Command-line tool to back up a MySQL database to disk, via mysqldump.**

"""

import argparse
import datetime
import getpass
import logging
import os
import subprocess
import sys
from typing import List

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

log = logging.getLogger(__name__)


def cmdargs(mysqldump: str,
            username: str,
            password: str,
            database: str,
            verbose: bool,
            with_drop_create_database: bool,
            max_allowed_packet: str,
            hide_password: bool = False) -> List[str]:
    """
    Returns command arguments for a ``mysqldump`` call.

    Args:
        mysqldump: ``mysqldump`` executable filename
        username: user name
        password: password
        database: database name
        verbose: verbose output?
        with_drop_create_database: produce commands to ``DROP`` the database
            and recreate it?
        max_allowed_packet: passed to ``mysqldump``
        hide_password: obscure the password (will break the arguments but
            provide a safe version to show the user)?

    Returns:
        list of command-line arguments
    """
    ca = [
        mysqldump,
        "-u", username,
        "-p{}".format("*****" if hide_password else password),
        "--max_allowed_packet={}".format(max_allowed_packet),
        "--hex-blob",  # preferable to raw binary in our .sql file
    ]
    if verbose:
        ca.append("--verbose")
    if with_drop_create_database:
        ca.extend([
            "--add-drop-database",
            "--databases",
            database
        ])
    else:
        ca.append(database)
        pass
    return ca


def main() -> None:
    """
    Command-line processor. See ``--help`` for details.
    """
    main_only_quicksetup_rootlogger()
    parser = argparse.ArgumentParser(
        description="Back up a specific MySQL database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "databases", nargs="+",
        help="Database(s) to back up")
    parser.add_argument(
        "--max_allowed_packet", default="1GB",
        help="Maximum size of buffer")
    parser.add_argument(
        "--mysqldump", default="mysqldump",
        help="mysqldump executable")
    parser.add_argument(
        "--username", default="root",
        help="MySQL user")
    parser.add_argument(
        "--password",
        help="MySQL password (AVOID THIS OPTION IF POSSIBLE; VERY INSECURE; "
             "VISIBLE TO OTHER PROCESSES; if you don't use it, you'll be "
             "prompted for the password)")
    parser.add_argument(
        "--with_drop_create_database", action="store_true",
        help="Include DROP DATABASE and CREATE DATABASE commands")
    parser.add_argument(
        "--verbose", action="store_true",
        help="Verbose output")
    args = parser.parse_args()

    password = args.password or getpass.getpass(
        prompt="MySQL password for user {}: ".format(args.username))

    output_files = []  # type: List[str]
    if args.with_drop_create_database:
        log.info("Note that the DROP DATABASE commands will look like they're "
                 "commented out, but they're not: "
                 "https://dba.stackexchange.com/questions/59294/")
        suffix = "_with_drop_create_database"
    else:
        suffix = ""
    for db in args.databases:
        now = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        outfilename = "{db}_{now}{suffix}.sql".format(db=db, now=now,
                                                      suffix=suffix)
        display_args = cmdargs(
            mysqldump=args.mysqldump,
            username=args.username,
            password=password,
            database=db,
            verbose=args.verbose,
            with_drop_create_database=args.with_drop_create_database,
            max_allowed_packet=args.max_allowed_packet,
            hide_password=True
        )
        actual_args = cmdargs(
            mysqldump=args.mysqldump,
            username=args.username,
            password=password,
            database=db,
            verbose=args.verbose,
            with_drop_create_database=args.with_drop_create_database,
            max_allowed_packet=args.max_allowed_packet,
            hide_password=False
        )
        log.info("Executing: " + repr(display_args))
        log.info("Output file: " + repr(outfilename))
        try:
            with open(outfilename, "w") as f:
                subprocess.check_call(actual_args, stdout=f)
        except subprocess.CalledProcessError:
            os.remove(outfilename)
            log.critical("Failed!")
            sys.exit(1)
        output_files.append(outfilename)
    log.info("Done. See:\n" + "\n".join("    " + x for x in output_files))
    if args.with_drop_create_database:
        log.info("To restore: mysql -u USER -p < BACKUP.sql")
    else:
        log.info("To restore: mysql -u USER -p DATABASE < BACKUP.sql")


if __name__ == '__main__':
    main()
