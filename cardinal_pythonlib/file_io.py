#!/usr/bin/env python
# cardinal_pythonlib/file_io.py

"""
===============================================================================
    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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

from contextlib import contextmanager
import csv
import fnmatch
import gzip
from html import escape
import io
import logging
from operator import attrgetter
import os
import shutil
import subprocess
import sys
import tempfile
from typing import (Any, BinaryIO, Generator, Iterable, IO, List, TextIO,
                    Tuple, Union)
import zipfile

# noinspection PyCompatibility
# import regex

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

UTF8 = "utf8"


# =============================================================================
# File opening
# =============================================================================

@contextmanager
def smart_open(filename: str, mode: str = 'Ur') -> IO:
    # https://stackoverflow.com/questions/17602878/how-to-handle-both-with-open-and-sys-stdout-nicely  # noqa
    # https://stackoverflow.com/questions/1744989/read-from-file-or-stdin/29824059#29824059  # noqa
    if filename == '-':
        if mode is None or mode == '' or 'r' in mode:
            fh = sys.stdin
        else:
            fh = sys.stdout
    else:
        fh = open(filename, mode)
    try:
        yield fh
    finally:
        if filename is not '-':
            fh.close()


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
# More file input: generic generators
# =============================================================================

def gen_textfiles_from_filenames(
        filenames: Iterable[str]) -> Generator[TextIO, None, None]:
    for filename in filenames:
        with open(filename) as f:
            yield f


def gen_lines_from_textfiles(
        files: Iterable[TextIO]) -> Generator[str, None, None]:
    for file in files:
        for line in file:
            yield line


def gen_lower(x: Iterable[str]) -> Generator[str, None, None]:
    for string in x:
        yield string.lower()


def gen_lines_from_binary_files(
        files: Iterable[BinaryIO],
        encoding: str = UTF8) -> Generator[str, None, None]:
    # Strips out newlines
    for file in files:
        for byteline in file:
            line = byteline.decode(encoding).strip()
            yield line


def gen_files_from_zipfiles(
        zipfilenames_or_files: Iterable[Union[str, BinaryIO]],
        filespec: str,
        on_disk: bool = False) -> Generator[BinaryIO, None, None]:
    for zipfilename_or_file in zipfilenames_or_files:
        with zipfile.ZipFile(zipfilename_or_file) as zf:
            infolist = zf.infolist()  # type: List[zipfile.ZipInfo]
            infolist.sort(key=attrgetter('filename'))
            for zipinfo in infolist:
                if not fnmatch.fnmatch(zipinfo.filename, filespec):
                    continue
                log.debug("Reading subfile {}".format(zipinfo.filename))
                if on_disk:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        zf.extract(zipinfo.filename, tmpdir)
                        diskfilename = os.path.join(tmpdir, zipinfo.filename)
                        with open(diskfilename, 'rb') as subfile:
                            yield subfile
                else:
                    # Will not be seekable; e.g.
                    # https://stackoverflow.com/questions/12821961/
                    with zf.open(zipinfo.filename) as subfile:
                        yield subfile


def gen_part_from_line(lines: Iterable[str],
                       part_index: int,
                       splitter: str = None) -> Generator[str, None, None]:
    for line in lines:
        parts = line.split(splitter)
        yield parts[part_index]


def gen_part_from_iterables(iterables: Iterable[Any],
                            part_index: int) -> Generator[Any, None, None]:
    for iterable in iterables:
        yield iterable[part_index]


def gen_rows_from_csv_binfiles(
        csv_files: Iterable[BinaryIO],
        encoding: str = UTF8,
        skip_header: bool = False,
        **csv_reader_kwargs) -> Generator[Iterable[str], None, None]:
    dialect = csv_reader_kwargs.pop('dialect', None)
    for csv_file_bin in csv_files:
        # noinspection PyTypeChecker
        csv_file = io.TextIOWrapper(csv_file_bin, encoding=encoding)
        thisfile_dialect = dialect
        if thisfile_dialect is None:
            thisfile_dialect = csv.Sniffer().sniff(csv_file.read(1024))
            csv_file.seek(0)
        reader = csv.reader(csv_file, dialect=thisfile_dialect,
                            **csv_reader_kwargs)
        first = True
        for row in reader:
            if first:
                first = False
                if skip_header:
                    continue
            yield row


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
