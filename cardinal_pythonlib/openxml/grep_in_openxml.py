#!/usr/bin/env python3
# cardinal_pythonlib/openxml/grep_in_openxml.py

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

**Performs a grep (global-regular-expression-print) search of files in OpenXML
format, which is to say inside ZIP files. See the command-line help for
details.**

Version history:

- Written 28 Sep 2017.

Notes:

- use the ``vbindiff`` tool to show *how* two binary files differ.

"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import logging
import multiprocessing
import re
from sys import getdefaultencoding, stdin
from typing import Pattern
from zipfile import BadZipFile, ZipFile
import zlib

from cardinal_pythonlib.logs import (
    BraceStyleAdapter,
    main_only_quicksetup_rootlogger,
)
from cardinal_pythonlib.fileops import gen_filenames

log = BraceStyleAdapter(logging.getLogger(__name__))


def report_hit_filename(zipfilename: str, contentsfilename: str,
                        show_inner_file: bool) -> None:
    """
    For "hits": prints either the ``.zip`` filename, or the ``.zip`` filename
    and the inner filename.

    Args:
        zipfilename: filename of the ``.zip`` file
        contentsfilename: filename of the inner file
        show_inner_file: if ``True``, show both; if ``False``, show just the
            ``.zip`` filename

    Returns:

    """
    if show_inner_file:
        print("{} [{}]".format(zipfilename, contentsfilename))
    else:
        print(zipfilename)


def report_miss_filename(zipfilename: str) -> None:
    """
    For "misses": prints the zip filename.
    """
    print(zipfilename)


def report_line(zipfilename: str, contentsfilename: str, line: str,
                show_inner_file: bool) -> None:
    """
    Prints a line from a file, with the ``.zip`` filename and optionally also
    the inner filename.

    Args:
        zipfilename: filename of the ``.zip`` file
        contentsfilename: filename of the inner file
        line: the line from the inner file
        show_inner_file: if ``True``, show both filenames; if ``False``, show
            just the ``.zip`` filename
    """
    if show_inner_file:
        print("{} [{}]: {}".format(zipfilename, contentsfilename, line))
    else:
        print("{}: {}".format(zipfilename, line))


def parse_zip(zipfilename: str,
              regex: Pattern,
              invert_match: bool,
              files_with_matches: bool,
              files_without_match: bool,
              grep_inner_file_name: bool,
              show_inner_file: bool) -> None:
    """
    Implement a "grep within an OpenXML file" for a single OpenXML file, which
    is by definition a ``.zip`` file.

    Args:
        zipfilename: name of the OpenXML (zip) file
        regex: regular expression to match
        invert_match: find files that do NOT match, instead of ones that do?
        files_with_matches: show filenames of files with a match?
        files_without_match: show filenames of files with no match?
        grep_inner_file_name: search the names of "inner" files, rather than
            their contents?
        show_inner_file: show the names of the "inner" files, not just the
            "outer" (OpenXML) file?
    """
    assert not (files_without_match and files_with_matches)
    report_lines = (not files_without_match) and (not files_with_matches)
    report_hit_lines = report_lines and not invert_match
    report_miss_lines = report_lines and invert_match
    log.debug("Checking ZIP: " + zipfilename)
    found_in_zip = False
    try:
        with ZipFile(zipfilename, 'r') as zf:
            for contentsfilename in zf.namelist():
                log.debug("... checking file: " + contentsfilename)
                if grep_inner_file_name:
                    found_in_filename = bool(regex.search(contentsfilename))
                    found_in_zip = found_in_zip or found_in_filename
                    if files_with_matches and found_in_zip:
                        report_hit_filename(zipfilename, contentsfilename,
                                            show_inner_file)
                        return
                    if ((report_hit_lines and found_in_filename) or
                            (report_miss_lines and not found_in_filename)):
                        report_line(zipfilename, contentsfilename,
                                    contentsfilename, show_inner_file)
                else:
                    try:
                        with zf.open(contentsfilename, 'r') as file:
                            try:
                                for line in file.readlines():
                                    # log.debug("line: {!r}", line)
                                    found_in_line = bool(regex.search(line))
                                    found_in_zip = found_in_zip or found_in_line
                                    if files_with_matches and found_in_zip:
                                        report_hit_filename(zipfilename,
                                                            contentsfilename,
                                                            show_inner_file)
                                        return
                                    if ((report_hit_lines and found_in_line) or
                                            (report_miss_lines and
                                             not found_in_line)):
                                        report_line(zipfilename,
                                                    contentsfilename,
                                                    line, show_inner_file)
                            except EOFError:
                                pass
                    except RuntimeError as e:
                        log.warning(
                            "RuntimeError whilst processing {} [{}]: probably "
                            "encrypted contents; error was {!r}",
                            zipfilename, contentsfilename, e)
    except (zlib.error, BadZipFile) as e:
        log.debug("Invalid zip: {}; error was {!r}", zipfilename, e)
    if files_without_match and not found_in_zip:
        report_miss_filename(zipfilename)


def main() -> None:
    """
    Command-line handler for the ``grep_in_openxml`` tool.
    Use the ``--help`` option for help.
    """
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description="""
Performs a grep (global-regular-expression-print) search of files in OpenXML
format, which is to say inside ZIP files.

Note that you can chain; for example, to search for OpenXML files containing
both "armadillo" and "bonobo", you can do:

    grep_in_openxml -l armadillo *.pptx | grep_in_openxml -x -l bonobo
                    ^^                                    ^^
                print filenames                       read filenames from stdin

"""
    )
    parser.add_argument(
        "pattern",
        help="Regular expression pattern to apply."
    )
    parser.add_argument(
        "filename", nargs="*",
        help="File(s) to check. You can also specify directores if you use "
             "--recursive"
    )
    parser.add_argument(
        "--filenames_from_stdin", "-x", action="store_true",
        help="Take filenames from stdin instead, one line per filename "
             "(useful for chained grep)."
    )
    parser.add_argument(
        "--recursive", action="store_true",
        help="Allow search to descend recursively into any directories "
             "encountered."
    )
    # Flag abbreviations to match grep:
    parser.add_argument(
        "--ignore_case", "-i", action="store_true",
        help="Ignore case"
    )
    parser.add_argument(
        "--invert_match", "-v", action="store_true",
        help="Invert match"
    )
    parser.add_argument(
        "--files_with_matches", "-l", action="store_true",
        help="Show filenames of files with matches"
    )
    parser.add_argument(
        "--files_without_match", "-L", action="store_true",
        help="Show filenames of files with no match"
    )
    parser.add_argument(
        "--grep_inner_file_name", action="store_true",
        help="Search the NAMES of the inner files, not their contents."
    )
    parser.add_argument(
        "--show_inner_file", action="store_true",
        help="For hits, show the filenames of inner files, within each ZIP."
    )
    parser.add_argument(
        "--nprocesses", type=int, default=multiprocessing.cpu_count(),
        help="Specify the number of processes to run in parallel."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Verbose output"
    )
    args = parser.parse_args()
    main_only_quicksetup_rootlogger(
        level=logging.DEBUG if args.verbose else logging.INFO)
    if args.files_with_matches and args.files_without_match:
        raise ValueError("Can't specify both --files_with_matches (-l) and "
                         "--files_without_match (-L)!")
    if bool(args.filenames_from_stdin) == bool(args.filename):
        raise ValueError("Specify --filenames_from_stdin or filenames on the "
                         "command line, but not both")

    # Compile regular expression
    if args.grep_inner_file_name:
        final_pattern = args.pattern
    else:
        encoding = getdefaultencoding()
        final_pattern = args.pattern.encode(encoding)
    flags = re.IGNORECASE if args.ignore_case else 0
    log.debug("Using regular expression {!r} with flags {!r}",
              final_pattern, flags)
    regex = re.compile(final_pattern, flags)

    # Set up pool for parallel processing
    pool = multiprocessing.Pool(processes=args.nprocesses)

    # Iterate through files
    parse_kwargs = dict(
        regex=regex,
        invert_match=args.invert_match,
        files_with_matches=args.files_with_matches,
        files_without_match=args.files_without_match,
        grep_inner_file_name=args.grep_inner_file_name,
        show_inner_file=args.show_inner_file
    )
    if args.filenames_from_stdin:
        for line in stdin.readlines():
            zipfilename = line.strip()
            parallel_kwargs = {'zipfilename': zipfilename}
            parallel_kwargs.update(**parse_kwargs)
            pool.apply_async(parse_zip, [], parallel_kwargs)
    else:
        for zipfilename in gen_filenames(starting_filenames=args.filename,
                                         recursive=args.recursive):
            parallel_kwargs = {'zipfilename': zipfilename}
            parallel_kwargs.update(**parse_kwargs)
            pool.apply_async(parse_zip, [], parallel_kwargs)
    pool.close()
    pool.join()


if __name__ == '__main__':
    main()
