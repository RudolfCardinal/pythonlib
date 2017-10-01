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
from typing import Iterable, List, TextIO

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
    with open(filename, 'w') as f:
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
