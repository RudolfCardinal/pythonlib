#!/usr/bin/env python

"""
tools/reformat_source.py

===============================================================================

    Copyright (C) 2012-2019 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of CamCOPS.

    CamCOPS is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    CamCOPS is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with CamCOPS. If not, see <http://www.gnu.org/licenses/>.

===============================================================================

**Clean up source code.**

"""

import logging
from os import walk
from os.path import join, splitext
from sys import stdout
from typing import List, TextIO

from cardinal_pythonlib.fileops import relative_filename_within_dir
from cardinal_pythonlib.logs import BraceStyleAdapter

log = BraceStyleAdapter(logging.getLogger(__name__))

TRANSITION = "==============================================================================="  # noqa
CORRECT_SHEBANG = "#!/usr/bin/env python"
RST_COMMENT_LINE = ".."
SHEBANG_START = "#!"
TRIPLE_DOUBLEQUOTE = '"""'
RAW_TRIPLE_DOUBLEQUOTE = 'r"""'
BLANK = ""
MISSING_RST_TITLE = "**Missing title.**"

CR = "\r"
LF = "\n"
NL = LF
SPACE = " "
TAB = "\t"
HASH = "#"
HASH_SPACE = "# "
PYTHON_EXTENSION = ".py"


# =============================================================================
# PythonProcessor
# =============================================================================

class PythonProcessor(object):
    """
    Class to read a Python source file and reformat its shebang/docstring etc.
    """

    def __init__(self, full_path: str, top_dir: str,
                 correct_copyright_lines: List[str]) -> None:
        """

        Args:
            full_path:
                full path to source file
            top_dir:
                directory from which we calculate a relative filename to be
                shown
            correct_copyright_lines:
                list of lines (without newlines) representing the copyright
                docstring block, including the transition lines of equals
                symbols
        """
        self.full_path = full_path
        self.advertised_filename = relative_filename_within_dir(
            full_path, top_dir)
        self.correct_copyright_lines = correct_copyright_lines
        self.needs_rewriting = False
        self.source_lines = []  # type: List[str]
        self.dest_lines = []  # type: List[str]
        self._read_source()
        self._create_dest()

    def _read_source(self) -> None:
        """
        Reads the source file.
        """
        with open(self.full_path, "rt") as f:
            for linenum, line_with_nl in enumerate(f.readlines(), start=1):
                line_without_newline = (
                    line_with_nl[:-1] if line_with_nl.endswith(NL)
                    else line_with_nl
                )
                if TAB in line_without_newline:
                    self._warn("Tab character at line {}".format(linenum))
                if CR in line_without_newline:
                    self._warn("Carriage return character at line {} "
                               "(Windows CR+LF endings?)".format(linenum))
                self.source_lines.append(line_without_newline)

    def _create_dest(self) -> None:
        """
        Creates an internal representation of the destination file.

        This is where the thinking happens
        """
        in_body = False
        in_docstring = False
        in_copyright = False
        copyright_done = False
        docstring_done = False
        swallow_blanks_and_filename_in_docstring = False
        for linenum, sl in enumerate(self.source_lines, start=1):
            dl = sl

            if dl.endswith(SPACE):
                self._debug("Line {} ends in whitespace".format(linenum))
                dl = dl.rstrip()

            if not in_body:

                if linenum == 1:
                    # Shebang
                    if not dl.startswith(SHEBANG_START):
                        self._warn("File does not start with shebang; "
                                   "first line was {!r}".format(dl))
                        self._too_risky()
                        return
                    if dl != CORRECT_SHEBANG:
                        self._debug("Rewriting shebang; was {!r}".format(dl))
                    dl = CORRECT_SHEBANG

                if (linenum == 2 and dl.startswith(HASH_SPACE) and
                        dl.endswith(PYTHON_EXTENSION)):
                    self._debug(
                        "Removing filename comment: {!r}".format(dl))
                    dl = None

                elif TRIPLE_DOUBLEQUOTE in dl:
                    if (not dl.startswith(TRIPLE_DOUBLEQUOTE) and
                            not dl.startswith(RAW_TRIPLE_DOUBLEQUOTE)):
                        self._warn(
                            "Triple-quote not at start of line, as follows")
                        self._debug_line(linenum, dl)
                        self._too_risky()
                        return
                    if in_docstring:  # docstring finishing
                        in_docstring = False
                        docstring_done = True
                        in_body = True
                        # ... and keep dl, so we write the end of the
                        # docstring, potentially with e.g. "# noqa" on the end
                    elif not docstring_done:  # docstring starting
                        in_docstring = True
                        # self._critical("adding our new docstring")
                        # Write our new docstring's start
                        tdq = ""  # stops linter moaning
                        if dl.startswith(TRIPLE_DOUBLEQUOTE):
                            tdq = TRIPLE_DOUBLEQUOTE
                        elif dl.startswith(RAW_TRIPLE_DOUBLEQUOTE):
                            tdq = RAW_TRIPLE_DOUBLEQUOTE
                        else:
                            assert "Bug!"
                        self.dest_lines.append(tdq)
                        self.dest_lines.append(self.advertised_filename)
                        self.dest_lines.append(BLANK)
                        self.dest_lines.extend(self.correct_copyright_lines)
                        self.dest_lines.append(BLANK)
                        swallow_blanks_and_filename_in_docstring = True
                        if dl == tdq:
                            dl = None  # don't write another triple-quote line
                        else:
                            dl = dl[len(tdq):]

                elif in_docstring:
                    # Reading within the source docstring

                    if dl == TRANSITION:
                        if in_copyright:  # copyright finishing
                            in_copyright = False
                            copyright_done = True
                            dl = None  # we've already replaced with our own
                        elif not copyright_done:
                            in_copyright = True
                            dl = None  # we've already replaced with our own

                    elif in_copyright:
                        dl = None  # we've already replaced with our own

                    elif dl == RST_COMMENT_LINE:
                        dl = None  # remove these

                    elif swallow_blanks_and_filename_in_docstring:
                        # self._debug_line(linenum, dl)
                        if dl == BLANK or dl == self.advertised_filename:
                            dl = None
                        elif copyright_done:
                            swallow_blanks_and_filename_in_docstring = False

                elif not dl.startswith(HASH) and not dl == BLANK:
                    in_body = True

                    if not docstring_done:
                        # The source file didn't have a docstring!
                        new_docstring_lines = [
                            BLANK,
                            TRIPLE_DOUBLEQUOTE,
                            self.advertised_filename,
                            BLANK,
                        ] + self.correct_copyright_lines + [
                            BLANK,
                            MISSING_RST_TITLE,
                            BLANK,
                            TRIPLE_DOUBLEQUOTE
                        ]
                        self._warn("File had no docstring; adding one. "
                                   "Will need manual edit to add RST title. "
                                   "Search for {!r}".format(MISSING_RST_TITLE))
                        self.dest_lines[1:1] = new_docstring_lines

            if dl is not None:
                # self._debug_line(linenum, dl, "adding ")
                self.dest_lines.append(dl)

        self.needs_rewriting = self.dest_lines != self.source_lines

    @staticmethod
    def _debug_line(linenum: int, line: str, extramsg: str = "") -> None:
        """
        Writes a debugging report on a line.
        """
        log.critical("{}Line {}: {!r}", extramsg, linenum, line)

    def _logmsg(self, msg: str) -> str:
        """
        Formats a log message.
        """
        return "{}: {}".format(self.advertised_filename, msg)

    def _critical(self, msg: str) -> None:
        """
        Shows a critical message.
        """
        log.critical(self._logmsg(msg))

    def _warn(self, msg: str) -> None:
        """
        Shows a warning.
        """
        log.warning(self._logmsg(msg))

    def _info(self, msg: str) -> None:
        """
        Shows an info message.
        """
        log.info(self._logmsg(msg))

    def _debug(self, msg: str) -> None:
        """
        Shows a debugging message.
        """
        log.debug(self._logmsg(msg))

    def _too_risky(self) -> None:
        """
        Shows a warning and sets this file as not for processing
        """
        self._warn("Don't know how to process file")
        self.needs_rewriting = False

    def show(self) -> None:
        """
        Writes the destination to stdout.
        """
        self._write(stdout)

    def rewrite_file(self) -> None:
        """
        Rewrites the source file.
        """
        if not self.needs_rewriting:
            return
        self._info("Rewriting file")
        with open(self.full_path, "w") as outfile:
            self._write(outfile)

    def _write(self, destination: TextIO) -> None:
        """
        Writes the converted output to a destination.
        """
        for line in self.dest_lines:
            destination.write(line + NL)


# =============================================================================
# Top-level functions
# =============================================================================

def reformat_python_docstrings(top_dirs: List[str],
                               correct_copyright_lines: List[str],
                               show_only: bool = True,
                               rewrite: bool = False,
                               process_only_filenum: int = None) -> None:
    """
    Walk a directory, finding Python files and rewriting them.

    Args:
        top_dirs: list of directories to descend into
        correct_copyright_lines:
            list of lines (without newlines) representing the copyright
            docstring block, including the transition lines of equals
            symbols
        show_only: show results (to stdout) only; don't rewrite
        rewrite: write the changes
        process_only_filenum: only process this file number (1-based index);
            for debugging only
    """
    filenum = 0
    for top_dir in top_dirs:
        for dirpath, dirnames, filenames in walk(top_dir):
            for filename in filenames:
                fullname = join(dirpath, filename)
                extension = splitext(filename)[1]
                if extension != PYTHON_EXTENSION:
                    # log.debug("Skipping non-Python file: {}", fullname)
                    continue

                filenum += 1

                if process_only_filenum and filenum != process_only_filenum:
                    continue

                log.info("Processing file {}: {}", filenum, fullname)
                proc = PythonProcessor(
                    full_path=fullname,
                    top_dir=top_dir,
                    correct_copyright_lines=correct_copyright_lines)
                if show_only:
                    proc.show()
                elif rewrite:
                    proc.rewrite_file()
