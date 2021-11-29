#!/usr/bin/env python
# cardinal_pythonlib/tools/convert_mdb_to_mysql.py

# noinspection HttpUrlsUsage
"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

***Converts a .MDB file (Microsoft Access) database to MySQL, copying structure
and data.***

Uses the ``mdb-tools`` package.

Under Ubuntu, the following packages are required:

.. code-block: bash

    sudo apt-get install mdbtools mysql-server mysql-client mysql-admin

though you may also want these, if you're planning to use Python/ODBC with
MySQL:

.. code-block: bash

    sudo apt-get install mysql-navigator libmdbtools libmdbodbc unixodbc python-mysqldb python-pyodbc

What works:

- schema copied
- data copied

What doesn't work:

- indexes are not described by mdb-schema, so these must be recreated
- relationships are not supported by mdb-schema, so these must be recreated

We'll do this with calls to other command-line tools. See
http://nialldonegan.me/2007/03/10/converting-microsoft-access-mdb-into-csv-or-mysql-in-linux/

History

- REVISED 1 Jan 2013: mdb-schema syntax has changed (-S option gone).
  See https://github.com/brianb/mdbtools.
- REVISED 16 Jan 2017: conversion to Python 3.
- Fixed a bit more, 2020-01-19. Also type hinting.

"""  # noqa

import argparse
import getpass
import logging
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable, List, Optional, Union

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

log = logging.getLogger(__name__)


def get_command_output(
        arglist: List[str],
        encoding: str = sys.getdefaultencoding()) -> Optional[str]:
    log.debug("Executing command: {}".format(arglist))
    result = subprocess.check_output(arglist)
    return result.decode(encoding) if result else None


def get_pipe_series_output(
        commands: List[List[str]],
        inputstr: str = None,
        encoding: str = sys.getdefaultencoding()) -> Optional[str]:
    processes = []
    log.debug("Executing commands: {}".format(
        " -> ".join(" ".join(arglist) for arglist in commands))
    )
    for i in range(len(commands)):
        arglist = commands[i]
        if i == 0:  # first processes
            processes.append(subprocess.Popen(arglist,
                                              stdin=subprocess.PIPE,
                                              stdout=subprocess.PIPE))
        else:  # subsequent ones
            processes.append(subprocess.Popen(arglist,
                                              stdin=processes[i - 1].stdout,
                                              stdout=subprocess.PIPE))
    stdout_bytes = processes[-1].communicate(inputstr.encode(encoding))[0]
    # communicate() returns a tuple; 0=stdout, 1=stderr; so this returns stdout
    return stdout_bytes.decode(encoding) if stdout_bytes else None


def replace_type_in_sql(sql: str, fromstr: str, tostr: str) -> str:
    whitespaceregroup = r"([\ \t\n]+)"
    whitespaceorcommaregroup = r"([\ \t\),\n]+)"
    rg1 = r"\g<1>"
    rg2 = r"\g<2>"
    return re.sub(whitespaceregroup + fromstr + whitespaceorcommaregroup,
                  rg1 + tostr + rg2, sql,
                  0,
                  re.MULTILINE | re.IGNORECASE)


class PasswordPromptAction(argparse.Action):
    """
    This provides a command-line option to provide a password or read it
    interactively.

    Use it like this:

    .. code-block:: python

        parser.add_argument(
            '--password', type=str, action=PasswordPromptAction,
            help="MySQL password")

    Modified from
    https://stackoverflow.com/questions/27921629/python-using-getpass-with-argparse
    """  # noqa
    # noinspection PyShadowingBuiltins
    def __init__(self,
                 option_strings: List[str],
                 dest: str = None,
                 nargs: Union[int, str] = "?",  # 0 or 1
                 default: Any = None,
                 required: bool = False,
                 type: Callable[[str], Any] = None,
                 metavar: str = None,
                 help: str = None) -> None:
        super(PasswordPromptAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            default=default,
            required=required,
            metavar=metavar,
            type=type,
            help=help)

    def __call__(self,
                 parser: argparse.ArgumentParser,
                 args: argparse.Namespace,
                 values: Union[None, str, List[str]],
                 option_string: str = None) -> None:
        if isinstance(values, list) and len(values) == 1:
            password = values[0]
        else:
            password = values
        if not password:
            password = getpass.getpass()
        setattr(args, self.dest, password)


def main() -> None:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'mdbfile', type=str,
        help="Microsoft Access .MDB file to read")
    parser.add_argument(
        '--schemaonly', action='store_true',
        help="Print schema SQL only (otherwise: will create MySQL database and"
             " write schema and data)")
    parser.add_argument(
        '--host', type=str, default='127.0.0.1',  # not "localhost"
        help="MySQL hostname or IP address")
    parser.add_argument(
        '--port', type=int, default=3306,
        help="MySQL port number")
    parser.add_argument(
        '--user', type=str, default='root',
        help="MySQL username")
    parser.add_argument(
        '--password', type=str, action=PasswordPromptAction,
        help="MySQL password")
    parser.add_argument(
        '--mysqldb', type=str,
        help="MySQL database to use")
    parser.add_argument(
        '--create', action="store_true",
        help="Create database?")
    args = parser.parse_args()

    if not args.schemaonly and not args.mysqldb:
        raise ValueError("Must specify --mysqldb, unless --schemaonly is used")

    main_only_quicksetup_rootlogger(level=logging.DEBUG)

    # -------------------------------------------------------------------------
    log.info("Getting list of tables")
    # -------------------------------------------------------------------------
    tablecmd = ["mdb-tables", "-1", args.mdbfile]
    # ... -1: one per line (or table names with spaces will cause confusion)
    tables = get_command_output(tablecmd).splitlines()
    tables.sort(key=lambda s: s.lower())
    log.info("Tables: {}".format(tables))

    # -------------------------------------------------------------------------
    log.info("Fetching schema definition")
    # -------------------------------------------------------------------------
    schemacmd = [
        "mdb-schema",  # from Ubuntu package mdbtools
        args.mdbfile,  # database
        "mysql",  # backend
        "--no-drop-table",  # don't issue DROP TABLE statements (default)
        "--not-null",  # issue NOT NULL constraints (default)
        "--no-default-values",  # don't issue DEFAULT values (default)
        "--indexes",  # export INDEX statements (default)
        "--relations",  # export foreign key constraints (default)
    ]
    schemasyntax = get_command_output(schemacmd)

    # -------------------------------------------------------------------------
    log.info("Converting any schema syntax oddities to MySQL syntax")
    # -------------------------------------------------------------------------
    # JAN 2013: Since my previous script, mdb-schema's mysql dialect has got
    # much better. So, not much to do here.

    # "COMMENT ON COLUMN" produced by mdb-schema and rejected by MySQL:
    schemasyntax = re.sub("^COMMENT ON COLUMN.*$", "", schemasyntax, 0,
                          re.MULTILINE)

    log.info("Schema syntax:")
    print(schemasyntax)

    # -------------------------------------------------------------------------
    # Done?
    # -------------------------------------------------------------------------
    if args.schemaonly:
        return

    # -------------------------------------------------------------------------
    log.info("Creating new database")
    # -------------------------------------------------------------------------
    createmysqldbcmd = [
        "mysqladmin",
        "create", args.mysqldb,
        "--host={}".format(args.host),
        "--port={}".format(args.port),
        "--user={}".format(args.user),
        "--password={}".format(args.password)
    ]
    # We could omit the actual password and the user would be prompted, but we
    # need to send it this way later (see below), so this is not a huge
    # additional security weakness!
    # Linux/MySQL helpfully obscures the password in the "ps" list.
    log.info(get_command_output(createmysqldbcmd))

    # -------------------------------------------------------------------------
    log.info("Sending schema command to MySQL")
    # -------------------------------------------------------------------------
    mysqlcmd = [
        "mysql",
        "--host={}".format(args.host),
        "--port={}".format(args.port),
        "--database={}".format(args.mysqldb),
        "--user={}".format(args.user),
        "--password={}".format(args.password)
    ]
    # Regrettably, we need the password here, as stdin will come from a pipe
    print(get_pipe_series_output([mysqlcmd], schemasyntax))

    # -------------------------------------------------------------------------
    log.info("Copying data to MySQL")
    # -------------------------------------------------------------------------
    # For the data, we won't store the intermediate stuff in Python's memory,
    # 'cos it's vast; I had one odd single-character mutation
    # from "TimeInSession_ms" to "TimeInSession_mc" at row 326444 (perhaps
    # therefore 37Mb or so into a long string).
    # And I was trying to export ~1m records in that table alone.
    # We'll use pipes instead and let the OS deal with the memory management.

    # ... BUT (Jan 2013): now mdb-tools is better, text-processing not
    # necessary - can use temporary disk file
    # Turns out the bottleneck is the import to MySQL, not the export from MDB.
    # So see http://dev.mysql.com/doc/refman/5.5/en/optimizing-innodb-bulk-data-loading.html  # noqa
    # The massive improvement is by disabling autocommit. (Example source
    # database is 208M; largest table here is 554M as a textfile; it has
    # 1,686,075 rows.) This improvement was from 20 Hz to the whole database
    # in a couple of minutes (~13 kHz). Subsequent export from MySQL: takes a
    # second or two to write whole DB (177M textfile).

    for t in tables:
        log.info("Processing table {}".format(t))
        exportcmd = [
            'mdb-export',
            '-I', 'mysql',  # -I backend: INSERT statements, not CSV

            # MySQL's DATETIME field has this format: "YYYY-MM-DD HH:mm:SS"
            # so we want this from the export:
            '-D', '%Y-%m-%d %H:%M:%S',  # -D: date format
            # ... don't put any extra quotes around it.

            args.mdbfile,  # database
            t  # table
        ]
        with tempfile.NamedTemporaryFile(
                mode="wt",
                encoding=sys.getdefaultencoding()) as outfile:
            print("SET autocommit=0;", file=outfile)
            subprocess.call(exportcmd, stdout=outfile)
            print("\nCOMMIT;", file=outfile)
            outfile.flush()
            outfile.seek(0)
            subprocess.call(mysqlcmd, stdin=outfile)

    log.info("Finished.")


if __name__ == '__main__':
    main()
