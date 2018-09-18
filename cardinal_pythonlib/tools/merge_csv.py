#!/usr/bin/env python
# cardinal_pythonlib/tools/merge_csv.py

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

**Command-line tool to merge multiple comma-separated value (CSV) or
tab-separated value (TSV) files, as long as they don't have incompatible
headers.**

"""

import argparse
import csv
import logging
import sys
from typing import List, TextIO

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

log = logging.getLogger(__name__)


def merge_csv(filenames: List[str],
              outfile: TextIO = sys.stdout,
              input_dialect: str = 'excel',
              output_dialect: str = 'excel',
              debug: bool = False,
              headers: bool = True) -> None:
    """
    Amalgamate multiple CSV/TSV/similar files into one.

    Args:
        filenames: list of filenames to process
        outfile: file-like object to write output to
        input_dialect: dialect of input files, as passed to ``csv.reader``
        output_dialect: dialect to write, as passed to ``csv.writer``
        debug: be verbose?
        headers: do the files have header lines?
    """
    writer = csv.writer(outfile, dialect=output_dialect)
    written_header = False
    header_items = []  # type: List[str]
    for filename in filenames:
        log.info("Processing file " + repr(filename))
        with open(filename, 'r') as f:
            reader = csv.reader(f, dialect=input_dialect)
            if headers:
                if not written_header:
                    header_items = next(reader)
                    if debug:
                        log.debug("Header row: {}".format(repr(header_items)))
                    writer.writerow(header_items)
                    written_header = True
                else:
                    new_headers = next(reader)
                    if new_headers != header_items:
                        raise ValueError(
                            "Header line in file {filename} doesn't match - "
                            "it was {new} but previous was {old}".format(
                                filename=repr(filename),
                                new=repr(new_headers),
                                old=repr(header_items),
                            ))
                    if debug:
                        log.debug("Header row matches previous")
            else:
                if debug:
                    log.debug("No headers in use")
            for row in reader:
                if debug:
                    log.debug("Data row: {}".format(repr(row)))
                writer.writerow(row)


def main():
    """
    Command-line processor. See ``--help`` for details.
    """
    main_only_quicksetup_rootlogger()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filenames",
        nargs="+",
        help="Names of CSV/TSV files to merge"
    )
    parser.add_argument(
        "--outfile",
        default="-",
        help="Specify an output filename. If omitted or '-', stdout is used.",
    )
    parser.add_argument(
        "--inputdialect",
        default="excel",
        help="The input files' CSV/TSV dialect. Default: %(default)s.",
        choices=csv.list_dialects(),
    )
    parser.add_argument(
        "--outputdialect",
        default="excel",
        help="The output file's CSV/TSV dialect. Default: %(default)s.",
        choices=csv.list_dialects(),
    )
    parser.add_argument(
        "--noheaders",
        action="store_true",
        help="By default, files are assumed to have column headers. "
             "Specify this option to assume no headers.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Verbose debugging output.",
    )
    progargs = parser.parse_args()

    kwargs = {
        "filenames": progargs.filenames,
        "input_dialect": progargs.inputdialect,
        "output_dialect": progargs.outputdialect,
        "debug": progargs.debug,
        "headers": not progargs.noheaders,
    }
    if progargs.outfile == '-':
        log.info("Writing to stdout")
        merge_csv(outfile=sys.stdout, **kwargs)
    else:
        log.info("Writing to " + repr(progargs.outfile))
        with open(progargs.outfile, 'w') as outfile:
            # noinspection PyTypeChecker
            merge_csv(outfile=outfile, **kwargs)


if __name__ == '__main__':
    main()
