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
from enum import Enum
import logging
import multiprocessing
import os
import re
from sys import argv, getdefaultencoding, stdin
from typing import Optional, Union
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile
import zlib

from rich_argparse import RawDescriptionRichHelpFormatter

from cardinal_pythonlib.logs import (
    main_only_quicksetup_rootlogger,
)
from cardinal_pythonlib.fileops import gen_filenames

log = logging.getLogger(__name__)


class GrepSearchSubstrate(Enum):
    XML_TEXT = 1
    RAW_TEXT = 2
    INNER_FILENAME = 3


class GrepReportContent(Enum):
    CONTENTS_MATCHING = 1
    CONTENTS_NOT_MATCHING = 2
    FILENAMES_MATCHING = 3
    FILENAMES_NOT_MATCHING = 4


class GrepMode:
    def __init__(
        self,
        pattern: str,
        ignore_case: bool = False,
        search_mode: Optional[GrepSearchSubstrate] = None,
        search_raw_text: bool = False,
        search_inner_filename: bool = False,
        report_mode: Optional[GrepReportContent] = None,
        report_invert_match: bool = False,
        report_files_with_matches: bool = False,
        report_files_without_match: bool = False,
        display_no_filename: bool = False,
        display_inner_filename: bool = False,
    ) -> None:
        """
        Args:
            pattern:
                What pattern to search for?
            ignore_case:
                Use a case-insensitive search.

            search_mode:
                Where to search? Specify an enum-based search mode directly.
            search_raw_text:
                Boolean flag alternative to search_mode. Search raw text
                (rather than the default of XML node text)? (Cannot be combined
                with search_mode, or search_inner_filename.)
            search_inner_filename:
                Boolean flag alternative to search_mode. Search inner filename
                (rather than the default of XML node text)? (Cannot be combined
                with search_mode, or search_raw_text.)

            report_mode:
                How to report? Specify an enum-based report mode directly.
            report_invert_match:
                Boolean flag alternative to report_mode. Inverts grep-like
                behaviour, reporting lines that do not match. (Cannot be
                combined with report_files_without_match or
                report_files_with_matches.)
            report_files_with_matches:
                Boolean flag alternative to report_mode. Show filenames of
                files with matches. (Cannot be combined with invert_match or
                report_files_without_match.)
            report_files_without_match:
                Boolean flag alternative to report_mode. Show filenames of
                files without matches. (Cannot be combined with invert_match or
                report_files_with_matches.)

            display_no_filename:
                For hits, omit the filename of the OpenXML (ZIP) file.
            display_inner_filename:
                For hits, show the filenames of inner files, within each
                OpenXML (ZIP) file.
        """
        # self.search_mode: what to search
        if search_mode is not None:
            if search_raw_text or search_inner_filename:
                raise ValueError(
                    "Can't specify search_raw_text or search_inner_filename "
                    "if you specify search_mode"
                )
            self.search_mode = search_mode
        else:
            if search_raw_text and search_inner_filename:
                raise ValueError(
                    "Can't specify both 'search_raw_text' and "
                    "'search_inner_filename' options"
                )
            if search_raw_text:
                self.search_mode = GrepSearchSubstrate.RAW_TEXT
            elif search_inner_filename:
                self.search_mode = GrepSearchSubstrate.INNER_FILENAME
            else:
                # Default is nothing is specified
                self.search_mode = GrepSearchSubstrate.XML_TEXT

        self.invert_match = report_invert_match

        # self.regex: what to search for
        self.pattern = pattern
        self.ignore_case = ignore_case
        if self.use_byte_regex:
            # Create a regex for type: bytes
            encoding = getdefaultencoding()
            final_pattern = pattern.encode(encoding)
        else:
            # Create a regex for type: str
            final_pattern = pattern
        flags = re.IGNORECASE if ignore_case else 0
        self.regex = re.compile(final_pattern, flags)

        # self.report_mode: what to report
        n_report_booleans = sum(
            [
                report_invert_match,
                report_files_with_matches,
                report_files_without_match,
            ]
        )
        if report_mode is not None:
            if n_report_booleans > 0:
                raise ValueError(
                    "Can't specify report_invert_match, "
                    "report_files_with_matches, or report_files_without_match "
                    "if you specify report_mode"
                )
            self.report_mode = report_mode
        else:
            if n_report_booleans > 1:
                raise ValueError(
                    "Specify at most one of: report_invert_match, "
                    "report_files_with_matches, report_files_without_match"
                )
            if report_invert_match:
                self.report_mode = GrepReportContent.CONTENTS_NOT_MATCHING
            elif report_files_with_matches:
                self.report_mode = GrepReportContent.FILENAMES_MATCHING
            elif report_files_without_match:
                self.report_mode = GrepReportContent.FILENAMES_NOT_MATCHING
            else:
                # default
                self.report_mode = GrepReportContent.CONTENTS_MATCHING

        self.display_no_filename = display_no_filename
        self.display_inner_filename = display_inner_filename

    def __repr__(self) -> str:
        return (
            f"GrepMode(pattern={self.pattern!r}, "
            f"ignore_case={self.ignore_case}, "
            f"search_mode={self.search_mode}, "
            f"report_mode={self.report_mode}, "
            f"display_no_filename={self.display_no_filename}, "
            f"display_inner_filename={self.display_inner_filename})"
        )

    def __str__(self) -> str:
        return repr(self)

    @property
    def use_byte_regex(self) -> bool:
        return self.search_mode == GrepSearchSubstrate.RAW_TEXT

    @property
    def report_hit_lines(self) -> bool:
        return self.report_mode == GrepReportContent.CONTENTS_MATCHING

    @property
    def report_miss_lines(self) -> bool:
        return self.report_mode == GrepReportContent.CONTENTS_NOT_MATCHING

    @property
    def report_files_with_matches(self) -> bool:
        return self.report_mode == GrepReportContent.FILENAMES_MATCHING

    @property
    def report_files_without_match(self) -> bool:
        return self.report_mode == GrepReportContent.FILENAMES_NOT_MATCHING


def report_hit_filename(
    zipfilename: str, inner_filename: str, display_inner_filename: bool
) -> None:
    """
    For "hits": prints either the ``.zip`` filename, or the ``.zip`` filename
    and the inner filename.

    Args:
        zipfilename:
            Filename of the outer OpenXML/zip file.
        inner_filename:
            Filename of the inner file.
        display_inner_filename:
            If True, show both outer and inner filename; if False, show just
            the outer (OpenXML/zip) filename.
    """
    if display_inner_filename:
        print(f"{zipfilename} [{inner_filename}]")
    else:
        print(zipfilename)


def report_miss_filename(zipfilename: str) -> None:
    """
    For "misses": prints the zip filename.
    """
    print(zipfilename)


def report_line(
    zipfilename: str,
    inner_filename: str,
    line: Union[bytes, str],
    display_no_filename: bool,
    display_inner_filename: bool,
) -> None:
    """
    Prints a line from a file, with the ``.zip`` filename and optionally also
    the inner filename.

    Args:
        zipfilename:
            Filename of the ``.zip`` file.
        inner_filename:
            Filename of the inner file.
        line:
            The line from the inner file.
        display_no_filename:
            Skip display of the outer filename.
        display_inner_filename:
            (Only applicable if no_filename is False.) If True, show both
            outer and inner filename; if False, show just the outer
            (OpenXML/zip) filename.
    """
    if display_no_filename:
        print(line)
    elif display_inner_filename:
        print(f"{zipfilename} [{inner_filename}]: {line}")
    else:
        print(f"{zipfilename}: {line}")


def parse_zip(zipfilename: str, mode: GrepMode) -> None:
    """
    Implement a "grep within an OpenXML file" for a single OpenXML file, which
    is by definition a ``.zip`` file.

    Args:
        zipfilename:
            Name of the OpenXML (zip) file.
        mode:
            Object configuring grep-type mode.
    """
    log.debug(f"Checking OpenXML ZIP: {zipfilename}")

    # Cache for speed:
    search_mode = mode.search_mode
    regex_search = mode.regex.search
    report_files_with_matches = mode.report_files_with_matches
    report_hit_lines = mode.report_hit_lines
    report_miss_lines = mode.report_miss_lines
    display_no_filename = mode.display_no_filename
    display_inner_filename = mode.display_inner_filename

    # Local data:
    found_in_zip = False
    # Have we found something in this zip file? May be used for early abort.

    def _report(
        _found_locally: bool,
        _innerfilename: str,
        _to_report: Union[bytes, str],
    ) -> bool:
        """
        Reporting function. This gets called more often than you might think,
        including for lines that do not need reporting, but this is to simplify
        the handling of "invert_match" (which may require all non-match lines
        to be reported).

        Arguments:
            _found_locally:
                Have we found a match in a current line?
            _innerfilename:
                The name of the inner file we are currently searching.
            _to_report:
                The text (usually a line, possibly the inner filename) that
                should be reported, if we report something. It might be
                matching text, or non-matching text.

        Returns:
            Ae we done for this ZIP file (should the outer function return)?
        """
        if report_files_with_matches and found_in_zip:
            report_hit_filename(
                zipfilename=zipfilename,
                inner_filename=_innerfilename,
                display_inner_filename=display_inner_filename,
            )
            return True
        if (report_hit_lines and _found_locally) or (
            report_miss_lines and not _found_locally
        ):
            report_line(
                zipfilename=zipfilename,
                inner_filename=_innerfilename,
                line=_to_report,
                display_no_filename=display_no_filename,
                display_inner_filename=display_inner_filename,
            )
        return False

    def _search_inner_file(zf: ZipFile, innerfilename: str) -> bool:
        """
        Deal with a single inner file.

        Arguments:
            zf:
                zip file
            innerfilename:
                inner filename

        Returns:
            Ae we done for this ZIP file (should the outer function return)?
        """
        nonlocal found_in_zip
        if search_mode == GrepSearchSubstrate.INNER_FILENAME:
            # -----------------------------------------------------------------
            # Search the (inner) filename
            # -----------------------------------------------------------------
            # log.debug("... ... searching filename")
            found_in_filename = bool(regex_search(innerfilename))
            found_in_zip |= found_in_filename
            done = _report(
                _found_locally=found_in_filename,
                _innerfilename=innerfilename,
                _to_report=innerfilename,
            )
            return done

        if search_mode == GrepSearchSubstrate.RAW_TEXT:
            # -----------------------------------------------------------------
            # Search textually, line by line
            # ---------------------------------------------------------
            # log.debug("... ... searching plain text")
            try:
                with zf.open(innerfilename, "r") as file:
                    try:
                        for line in file.readlines():
                            # "line" is of type "bytes"
                            found_in_line = bool(regex_search(line))
                            found_in_zip |= found_in_line
                            done = _report(
                                _found_locally=found_in_line,
                                _innerfilename=innerfilename,
                                _to_report=line,
                            )
                            if done:
                                return True
                    except EOFError:
                        pass
            except RuntimeError as e:
                log.warning(
                    f"RuntimeError whilst processing {zipfilename} "
                    f"[{innerfilename}]: probably encrypted contents; "
                    f"error was {e!r}"
                )
        else:
            # -----------------------------------------------------------------
            # Search the text contents of XML
            # -----------------------------------------------------------------
            # log.debug("... ... searching XML contents")
            try:
                with zf.open(innerfilename, "r") as file:
                    data_str = file.read()
                    try:
                        tree = ElementTree.fromstring(data_str)
                    except ElementTree.ParseError:
                        log.debug(
                            f"... ... skipping (not XML): " f"{innerfilename}"
                        )
                        return False
                    for elem in tree.iter():
                        line = elem.text
                        if not line:
                            continue
                        found_in_line = bool(regex_search(line))
                        found_in_zip |= found_in_line
                        done = _report(
                            _found_locally=found_in_line,
                            _innerfilename=innerfilename,
                            _to_report=line,
                        )
                        if done:
                            return True
            except RuntimeError as e:
                log.warning(
                    f"RuntimeError whilst processing {zipfilename} "
                    f"[{innerfilename}]: probably encrypted contents; "
                    f"error was {e!r}"
                )
        return False

    # Process the zip file
    try:
        with ZipFile(zipfilename, "r") as _zf:
            # Iterate through inner files
            for _innerfilename in _zf.namelist():
                log.debug(f"... checking inner file: {_innerfilename}")
                zip_done = _search_inner_file(_zf, _innerfilename)
                if zip_done:
                    return
    except (zlib.error, BadZipFile) as exc:
        log.warning(f"Invalid zip: {zipfilename}; error was {exc!r}")
    except IsADirectoryError:
        log.warning(f"Skipping directory: {zipfilename}")
    if mode.report_files_without_match and not found_in_zip:
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

    find . -type f -iname "*.doc*" -exec {exe_name} -l -i "laurel" {{}} \; | {exe_name} -x -l -i "hardy"
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
        "--invert_match",
        "-v",
        action="store_true",
        help="Invert match (show content lines not matching the search "
        "pattern)",
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
        "--no_filename",
        action="store_true",
        help="For hits, omit the filename of the OpenXML file.",
    )
    parser.add_argument(
        "--show_inner_filename",
        action="store_true",
        help="For hits, show the filenames of inner files, within each "
        "OpenXML (ZIP) file. Ignored if --no_filename is true.",
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

    if args.grep_raw_text and args.grep_inner_file_name:
        raise ValueError(
            "Can't specify both --grep_raw_text and --grep_inner_file_name"
        )
    n_report_booleans = sum(
        [
            args.invert_match,
            args.files_with_matches,
            args.files_without_match,
        ]
    )
    if n_report_booleans > 1:
        raise ValueError(
            "Specify at most one of --invert_match (-v), "
            "--files_with_matches (-l), "
            "--files_without_match (-L)"
        )
    if bool(args.filenames_from_stdin) == bool(args.filename):
        raise ValueError(
            "Specify --filenames_from_stdin or filenames on the "
            "command line, but not both"
        )

    main_only_quicksetup_rootlogger(
        level=logging.DEBUG if args.verbose else logging.INFO
    )
    mode = GrepMode(
        pattern=args.pattern,
        ignore_case=args.ignore_case,
        search_raw_text=args.grep_raw_text,
        search_inner_filename=args.grep_inner_file_name,
        report_invert_match=args.invert_match,
        report_files_with_matches=args.files_with_matches,
        report_files_without_match=args.files_without_match,
        display_no_filename=args.no_filename,
        display_inner_filename=args.show_inner_filename,
    )
    log.debug(f"Mode: {mode}")

    # Iterate through files
    # - Common arguments
    common_kwargs = dict(mode=mode)
    # - Filenames, as iterator
    if args.filenames_from_stdin:
        line_it = (line.strip() for line in stdin.readlines())
        zipfilename_it = filter(None, line_it)  # remove any blanks
    else:
        zipfilename_it = gen_filenames(
            starting_filenames=args.filename, recursive=args.recursive
        )
    # - Combined arguments, as iterator
    arg_it = (
        dict(zipfilename=zipfilename, **common_kwargs)
        for zipfilename in zipfilename_it
    )
    if args.nprocesses == 1:
        # Force serial processing (useful for debugging).
        for kwargs in arg_it:
            parse_zip(**kwargs)
    else:
        # Set up pool for parallel processing
        pool = multiprocessing.Pool(processes=args.nprocesses)
        # Launch in parallel
        jobs = [pool.apply_async(parse_zip, [], kwargs) for kwargs in arg_it]
        # Stop entry to the pool (close) and wait for children (join).
        # See https://stackoverflow.com/questions/38271547/.
        pool.close()
        pool.join()
        # Collect results, re-raising any exceptions. (Otherwise they will be
        # invisible.) See https://stackoverflow.com/questions/6728236/.
        for j in jobs:
            j.get()


if __name__ == "__main__":
    main()
