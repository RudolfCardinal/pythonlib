#!/usr/bin/env python3
# cardinal_pythonlib/openxml/grep_in_openxml.py

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

**Performs a grep (global-regular-expression-print) search of files in OpenXML
format, which is to say inside ZIP files. See the command-line help for
details.**

Version history:

- Written 28 Sep 2017.

Notes:

- use the ``vbindiff`` tool to show *how* two binary files differ.

"""

from argparse import ArgumentParser
import logging
import multiprocessing
import os
import re
from sys import argv, getdefaultencoding, stdin
from typing import Pattern, Union
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile
import zlib

from rich_argparse import RawDescriptionRichHelpFormatter

from cardinal_pythonlib.logs import (
    main_only_quicksetup_rootlogger,
)
from cardinal_pythonlib.fileops import gen_filenames

log = logging.getLogger(__name__)


def report_hit_filename(
    zipfilename: str, contentsfilename: str, show_inner_file: bool
) -> None:
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
        print(f"{zipfilename} [{contentsfilename}]")
    else:
        print(zipfilename)


def report_miss_filename(zipfilename: str) -> None:
    """
    For "misses": prints the zip filename.
    """
    print(zipfilename)


def report_line(
    zipfilename: str,
    contentsfilename: str,
    line: Union[bytes, str],
    show_inner_file: bool,
) -> None:
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
        print(f"{zipfilename} [{contentsfilename}]: {line}")
    else:
        print(f"{zipfilename}: {line}")


def parse_zip(
    zipfilename: str,
    regex: Pattern,
    invert_match: bool,
    files_with_matches: bool,
    files_without_match: bool,
    grep_inner_file_name: bool,
    grep_raw_text: bool,
    show_inner_file: bool,
) -> None:
    """
    Implement a "grep within an OpenXML file" for a single OpenXML file, which
    is by definition a ``.zip`` file.

    Args:
        zipfilename:
            Name of the OpenXML (zip) file.
        regex:
            Regular expression to match.
        invert_match:
            Find files that do NOT match, instead of ones that do?
        files_with_matches:
            Show filenames of OpenXML (zip) files with a match?
        files_without_match:
            Show filenames of OpenXML (zip) files with no match?
        grep_inner_file_name:
            Search the names of "inner" files, rather than their contents?
        grep_raw_text:
            Search the raw text, not the XML node text contents.
        show_inner_file:
            Show the names of the "inner" files, not just the "outer" (OpenXML)
            file?
    """
    # Check arguments
    assert not (files_without_match and files_with_matches)
    assert not (grep_inner_file_name and grep_raw_text)

    # Precalculate some reporting flags
    _report_lines = (not files_without_match) and (not files_with_matches)
    report_hit_lines = _report_lines and not invert_match
    report_miss_lines = _report_lines and invert_match

    log.debug(f"Checking OpenXML ZIP: {zipfilename}")
    found_in_zip = False
    # ... Have we found something in this zip file? May be used for early
    #     abort.

    def _report(
        _found_in_zip: bool,
        _found_locally: bool,
        _contentsfilename: str,
        _to_report: Union[bytes, str],
    ) -> bool:
        """
        Reporting function. This gets called more often than you might think,
        including for lines that do not need reporting, but this is to simplify
        the handling of "invert_match" (which may require all non-match lines
        to be reported).

        Arguments:
            _found_in_zip:
                Have we found a match in this ZIP file?
            _found_locally:
                Have we found a match in a current line?
            _contentsfilename:
                The name of the inner file we are currently searching.
            _to_report:
                The text (usually a line, possibly the inner filename) that
                should be reported, if we report something. It might be
                matching text, or non-matching text.

        Returns:
            Ae we done for this ZIP file (should the outer function return)?
        """
        if files_with_matches and _found_in_zip:
            report_hit_filename(
                zipfilename, _contentsfilename, show_inner_file
            )
            return True
        if (report_hit_lines and _found_locally) or (
            report_miss_lines and not _found_locally
        ):
            report_line(
                zipfilename,
                _contentsfilename,
                _to_report,
                show_inner_file,
            )
        return False

    try:
        with ZipFile(zipfilename, "r") as zf:
            # Iterate through inner files
            for contentsfilename in zf.namelist():
                log.debug(f"... checking inner file: {contentsfilename}")
                if grep_inner_file_name:
                    # ---------------------------------------------------------
                    # Search the (inner) filename
                    # ---------------------------------------------------------
                    log.debug("... ... searching filename")
                    found_in_filename = bool(regex.search(contentsfilename))
                    found_in_zip = found_in_zip or found_in_filename
                    done = _report(
                        _found_in_zip=found_in_zip,
                        _found_locally=found_in_filename,
                        _contentsfilename=contentsfilename,
                        _to_report=contentsfilename,
                    )
                    if done:
                        return
                elif grep_raw_text:
                    # ---------------------------------------------------------
                    # Search textually, line by line
                    # ---------------------------------------------------------
                    # log.debug("... ... searching plain text")
                    try:
                        with zf.open(contentsfilename, "r") as file:
                            try:
                                for line in file.readlines():
                                    # "line" is of type "bytes"
                                    found_in_line = bool(regex.search(line))
                                    found_in_zip = (
                                        found_in_zip or found_in_line
                                    )
                                    done = _report(
                                        _found_in_zip=found_in_zip,
                                        _found_locally=found_in_line,
                                        _contentsfilename=contentsfilename,
                                        _to_report=line,
                                    )
                                    if done:
                                        return
                            except EOFError:
                                pass
                    except RuntimeError as e:
                        log.warning(
                            f"RuntimeError whilst processing {zipfilename} "
                            f"[{contentsfilename}]: probably encrypted "
                            f"contents; error was {e!r}"
                        )
                else:
                    # ---------------------------------------------------------
                    # Search the text contents of XML
                    # ---------------------------------------------------------
                    # log.debug("... ... searching XML contents")
                    try:
                        with zf.open(contentsfilename, "r") as file:
                            data_str = file.read()
                            try:
                                tree = ElementTree.fromstring(data_str)
                            except ElementTree.ParseError:
                                log.debug(
                                    f"... ... skipping (not XML): "
                                    f"{contentsfilename}"
                                )
                            for elem in tree.iter():
                                line = elem.text
                                if not line:
                                    continue
                                found_in_line = bool(regex.search(line))
                                found_in_zip = found_in_zip or found_in_line
                                done = _report(
                                    _found_in_zip=found_in_zip,
                                    _found_locally=found_in_line,
                                    _contentsfilename=contentsfilename,
                                    _to_report=line,
                                )
                                if done:
                                    return
                    except RuntimeError as e:
                        log.warning(
                            f"RuntimeError whilst processing {zipfilename} "
                            f"[{contentsfilename}]: probably encrypted "
                            f"contents; error was {e!r}"
                        )
    except (zlib.error, BadZipFile) as e:
        log.debug(f"Invalid zip: {zipfilename}; error was {e!r}")
    if files_without_match and not found_in_zip:
        report_miss_filename(zipfilename)


def main() -> None:
    """
    Command-line handler for the ``grep_in_openxml`` tool.
    Use the ``--help`` option for help.
    """
    exe_name = os.path.basename(argv[0]) or "grep_in_openxml"
    parser = ArgumentParser(
        formatter_class=RawDescriptionRichHelpFormatter,
        description=rf"""
Performs a grep (global-regular-expression-print) search of files in OpenXML
format, which is to say inside ZIP files.

TYPICAL USAGE. To find files in a tree, you can use the "find" tool. For
example, to find all ".docx" files in a directory (or its subdirectories) that
contain the phrase "armadillo country", you could use:

    find <STARTDIR> -type f -name "*.docx" -exec {exe_name} -l "armadillo country" {{}} \;

Or, if you don't need the restriction to ".docx" files, you could use this tool
directly, specifying a directory and "--recursive", as in

    {exe_name} -l --recursive "armadillo country" <STARTDIR>

CHAINING. Note that you can chain. For example, to find both "Laurel" and
"Hardy" in DOC/DOCX documents, in case-insensitive fashion:

    find . -type f -name "*.doc*" -exec {exe_name} -l -i "laurel" {{}} \; | {exe_name} -x -l -i "hardy"
""",  # noqa: E501
    )
    parser.add_argument("pattern", help="Regular expression pattern to apply.")
    parser.add_argument(
        "filename",
        nargs="*",
        help="File(s) to check. You can also specify directores if you use "
        "--recursive",
    )
    parser.add_argument(
        "--filenames_from_stdin",
        "-x",
        action="store_true",
        help="Take filenames from stdin instead, one line per filename "
        "(useful for chained grep).",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Allow search to descend recursively into any directories "
        "encountered.",
    )
    # Flag abbreviations to match grep:
    parser.add_argument(
        "--ignore_case", "-i", action="store_true", help="Ignore case"
    )
    parser.add_argument(
        "--invert_match", "-v", action="store_true", help="Invert match"
    )
    parser.add_argument(
        "--files_with_matches",
        "-l",
        action="store_true",
        help="Show filenames of files with matches",
    )
    parser.add_argument(
        "--files_without_match",
        "-L",
        action="store_true",
        help="Show filenames of files with no match",
    )
    parser.add_argument(
        "--grep_inner_file_name",
        action="store_true",
        help="Search the NAMES of the inner files, not their contents.",
    )
    parser.add_argument(
        "--grep_raw_text",
        action="store_true",
        help="Search the raw text, not the XML node text contents.",
    )
    parser.add_argument(
        "--show_inner_file",
        action="store_true",
        help="For hits, show the filenames of inner files, within each ZIP.",
    )
    parser.add_argument(
        "--nprocesses",
        type=int,
        default=multiprocessing.cpu_count(),
        help="Specify the number of processes to run in parallel.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Verbose output"
    )
    args = parser.parse_args()
    main_only_quicksetup_rootlogger(
        level=logging.DEBUG if args.verbose else logging.INFO
    )
    if args.files_with_matches and args.files_without_match:
        raise ValueError(
            "Can't specify both --files_with_matches (-l) and "
            "--files_without_match (-L)!"
        )
    if bool(args.filenames_from_stdin) == bool(args.filename):
        raise ValueError(
            "Specify --filenames_from_stdin or filenames on the "
            "command line, but not both"
        )

    if args.grep_raw_text and args.grep_inner_file_name:
        raise ValueError(
            "Can't specify both --grep_raw_text and --grep_inner_file_name"
        )

    # Compile regular expression
    if args.grep_raw_text:
        # Create a regex for type: bytes
        encoding = getdefaultencoding()
        final_pattern = args.pattern.encode(encoding)
    else:
        # Create a regex for type: str
        final_pattern = args.pattern
    flags = re.IGNORECASE if args.ignore_case else 0
    log.debug(
        f"Using regular expression {final_pattern!r} with flags {flags!r}"
    )
    regex = re.compile(final_pattern, flags)

    # Iterate through files
    # - Common arguments
    parse_kwargs = dict(
        regex=regex,
        invert_match=args.invert_match,
        files_with_matches=args.files_with_matches,
        files_without_match=args.files_without_match,
        grep_inner_file_name=args.grep_inner_file_name,
        grep_raw_text=args.grep_raw_text,
        show_inner_file=args.show_inner_file,
    )
    # - Filenames, as iterator
    if args.filenames_from_stdin:
        zipfilename_it = (line.strip() for line in stdin.readlines())
    else:
        zipfilename_it = gen_filenames(
            starting_filenames=args.filename, recursive=args.recursive
        )
    # - Combined arguments, as iterator
    arg_it = (
        dict(zipfilename=zipfilename, **parse_kwargs)
        for zipfilename in zipfilename_it
    )
    # - Set up pool for parallel processing
    pool = multiprocessing.Pool(processes=args.nprocesses)
    # - Launch in parallel
    jobs = [pool.apply_async(parse_zip, [], kwargs) for kwargs in arg_it]
    # - Stop entry to the pool (close) and wait for children (join).
    #   https://stackoverflow.com/questions/38271547/
    pool.close()
    pool.join()
    # - Collect results, re-raising any exceptions.
    #   (Otherwise they will be invisible.)
    #   https://stackoverflow.com/questions/6728236/
    for j in jobs:
        j.get()


if __name__ == "__main__":
    main()
