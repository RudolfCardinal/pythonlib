#!/usr/bin/env python
# cardinal_pythonlib/file_io.py

"""
===============================================================================
    Copyright (C) 2009-2017 Rudolf Cardinal (rudolf@pobox.com).

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

Support functions for file I/O.

"""

import gzip
from html import escape
import io
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Iterable, List, TextIO, Tuple

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# File output
# =============================================================================

def writeline_nl(fileobj: TextIO, line: str) -> None:
    fileobj.write(line + '\n')


def writelines_nl(fileobj: TextIO, lines: Iterable[str]) -> None:
    # Since fileobj.writelines() doesn't add newlines...
    # http://stackoverflow.com/questions/13730107/writelines-writes-lines-without-newline-just-fills-the-file  # noqa
    fileobj.write('\n'.join(lines) + '\n')


def write_text(filename: str, text: str) -> None:
    with open(filename, 'w') as f:  # type: TextIO
        print(text, file=f)


def write_gzipped_text(basefilename: str, text: str) -> None:
    # Lintian wants non-timestamped gzip files, or it complains:
    # https://lintian.debian.org/tags/package-contains-timestamped-gzip.html
    # See http://stackoverflow.com/questions/25728472/python-gzip-omit-the-original-filename-and-timestamp  # noqa
    zipfilename = basefilename + '.gz'
    compresslevel = 9
    mtime = 0
    with open(zipfilename, 'wb') as f:
        with gzip.GzipFile(basefilename, 'wb', compresslevel, f, mtime) as gz:
            with io.TextIOWrapper(gz) as tw:
                tw.write(text)


# =============================================================================
# File input
# =============================================================================

def get_lines_without_comments(filename: str) -> List[str]:
    lines = []
    with open(filename) as f:
        for line in f:
            line = line.partition('#')[0]
            line = line.rstrip()
            line = line.lstrip()
            if line:
                lines.append(line)
    return lines


# =============================================================================
# File transformations
# =============================================================================

def webify_file(srcfilename: str, destfilename: str) -> None:
    """
    Rewrites a file from "srcfilename" to "destfilename", HTML-escaping it in
    the process.
    """
    with open(srcfilename) as infile, open(destfilename, 'w') as ofile:
        for line_ in infile:
            ofile.write(escape(line_))


def remove_gzip_timestamp(filename: str,
                          gunzip_executable: str = "gunzip",
                          gzip_executable: str = "gzip",
                          gzip_args: List[str] = None) -> None:
    """
    Uses external gunzip/gzip tools to remove a gzip timestamp.
    Necessary for Lintian.
    """
    gzip_args = gzip_args or [
        "-9",  # maximum compression (or Lintian moans)
        "-n",
    ]
    # gzip/gunzip operate on SINGLE files
    with tempfile.TemporaryDirectory() as dir_:
        basezipfilename = os.path.basename(filename)
        newzip = os.path.join(dir_, basezipfilename)
        with open(newzip, 'wb') as z:
            log.info(
                "Removing gzip timestamp: "
                "{} -> gunzip -c -> gzip -n -> {}".format(
                    basezipfilename, newzip))
            p1 = subprocess.Popen([gunzip_executable, "-c", filename],
                                  stdout=subprocess.PIPE)
            p2 = subprocess.Popen([gzip_executable] + gzip_args,
                                  stdin=p1.stdout, stdout=z)
            p2.communicate()
        shutil.copyfile(newzip, filename)  # copy back


# =============================================================================
# File modifications
# =============================================================================

def replace_in_file(filename: str, text_from: str, text_to: str) -> None:
    """
    Replaces text in a file.
    """
    log.info("Amending {}: {} -> {}".format(
        filename, repr(text_from), repr(text_to)))
    with open(filename) as infile:
        contents = infile.read()
    contents = contents.replace(text_from, text_to)
    with open(filename, 'w') as outfile:
        outfile.write(contents)


def replace_multiple_in_file(filename: str,
                             replacements: List[Tuple[str, str]]) -> None:
    """
    Replaces multiple from/to string pairs within a single file.
    """
    with open(filename) as infile:
        contents = infile.read()
    for text_from, text_to in replacements:
        log.info("Amending {}: {} -> {}".format(
            filename, repr(text_from), repr(text_to)))
        contents = contents.replace(text_from, text_to)
    with open(filename, 'w') as outfile:
        outfile.write(contents)


def convert_line_endings(filename: str, to_unix: bool = False,
                         to_windows: bool = False) -> None:
    """
    Converts a file from UNIX -> Windows line endings, or the reverse.
    """
    assert to_unix != to_windows
    with open(filename, "rb") as f:
        contents = f.read()
    windows_eol = b"\r\n"  # CR LF
    unix_eol = b"\n"  # LF
    if to_unix:
        log.info("Converting from Windows to UNIX line endings: {!r}".format(
            filename))
        src = windows_eol
        dst = unix_eol
    else:  # to_windows
        log.info("Converting from UNIX to Windows line endings: {!r}".format(
            filename))
        src = unix_eol
        dst = windows_eol
        if windows_eol in contents:
            log.info("... already contains at least one Windows line ending; "
                     "probably converted before; skipping")
            return
    contents = contents.replace(src, dst)
    with open(filename, "wb") as f:
        f.write(contents)


def is_line_in_file(filename: str, line: str) -> bool:
    """
    Detects whether a line is present within a file.
    """
    assert "\n" not in line
    with open(filename, "r") as file:
        for fileline in file:
            if fileline == line:
                return True
        return False


def add_line_if_absent(filename: str, line: str) -> None:
    """
    Adds a line (at the end) if it's not already in the file.
    """
    assert "\n" not in line
    if not is_line_in_file(filename, line):
        log.info("Appending line {!r} to file {!r}".format(line, filename))
        with open(filename, "a") as file:
            file.writelines([line])
