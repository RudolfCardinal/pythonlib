#!/usr/bin/env python
# cardinal_pythonlib/tools/pdf_to_booklet.py

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

RNC, 18 Nov 2017.

PURPOSE:

Take a PDF created with pdfnup or similar, with A4 sheets and two pages per
sheet, like this:

    PDF page 1      +-----+-----+
                    |     |     |
                    |  1  |  2  |
                    |     |     |
                    +-----+-----+

    PDF page 2      +-----+-----+
                    |     |     |
                    |  3  |  4  |
                    |     |     |
                    +-----+-----+

    PDF page 3      +-----+-----+
                    |     |     |
                    |  5  |  6  |
                    |     |     |
                    +-----+-----+

and create a similar PDF but like this:

    PDF page 1      +-----+-----+
                    |     |     |
                    |  6  |  1  |
                    |     |     |
                    +-----+-----+

    PDF page 2      +-----+-----+
                    |     |     |
                    |  1  |  2  |
                    |     |     |
                    +-----+-----+

    PDF page 3      +-----+-----+
                    |     |     |
                    |  1  |  2  |
                    |     |     |
                    +-----+-----+

so it can be printed double-sided and folded into an A5 booklet.

DEFINITIONS
    page = one side of a piece of paper BUT HERE, IN A BOOK CONTEXT, half that,
        i.e. what ends up as a book "page"
    pair = two pages, making up one side of a sheet/leaf
    sheet = one piece of paper (= leaf) (= 4 pages, here)

PRINTING
    It's our job here to make pairs from pages, and to create a PDF where each
    PDF page is a pair.

    It's the printer's job to make sheets from pages. When printing in duplex,
    you will need to use SHORT-EDGE BINDING (if you use long-edge binding, the
    reverse sides will be inverted).

"""

import argparse
import logging
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import List, Tuple
import unittest

from cardinal_pythonlib.logs import BraceStyleAdapter, main_only_quicksetup_rootlogger  # noqa

log = BraceStyleAdapter(logging.getLogger(__name__))

CONVERT = "convert"
MUTOOL = "mutool"
PDFJAM = "pdfjam"
# PDFNUP = "pdfnup"  # interface to pdfjam, but too restrictive
PDFTK = "pdftk"


# =============================================================================
# Calculate page sequence
# =============================================================================

def calc_n_sheets(n_pages: int) -> int:
    # noinspection PyTypeChecker
    return math.ceil(n_pages / 2)


def calc_n_virtual_pages(n_sheets: int) -> int:
    """
    Converts #sheets to #pages, but rounding up to a multiple of 4.
    """
    if n_sheets % 2 == 0:
        return n_sheets * 2
    else:
        return (n_sheets + 1) * 2


def page_sequence(n_sheets: int, one_based: bool = True) -> List[int]:
    """
    Generates the final page sequence from the starting number of sheets.
    """
    n_pages = calc_n_virtual_pages(n_sheets)
    assert n_pages % 4 == 0
    half_n_pages = n_pages // 2
    firsthalf = list(range(half_n_pages))
    secondhalf = list(reversed(range(half_n_pages, n_pages)))
    # Seen from the top of an UNFOLDED booklet (e.g. a stack of paper that's
    # come out of your printer), "firsthalf" are on the right (from top to
    # bottom: recto facing up, then verso facing down, then recto, then verso)
    # and "secondhalf" are on the left (from top to bottom: verso facing up,
    # then recto facing down, etc.).
    sequence = []  # type: List[int]
    top = True
    for left, right in zip(secondhalf, firsthalf):
        if not top:
            left, right = right, left
        sequence += [left, right]
        top = not top
    if one_based:
        sequence = [x + 1 for x in sequence]
    log.debug("{} sheets -> page sequence {!r}", n_sheets, sequence)
    return sequence


# =============================================================================
# PDF processor
# =============================================================================

def require(executable: str, explanation: str = "") -> None:
    assert shutil.which(executable), "Need {!r} on the PATH{}".format(
        executable, "; " + explanation if explanation else "")


def run(args: List[str],
        get_output: bool = False,
        encoding: str = sys.getdefaultencoding()) -> Tuple[str, str]:
    printable = " ".join(shlex.quote(x) for x in args).replace("\n", r"\n")
    log.debug("{}", printable)  # printable may have {} characters in
    if get_output:
        p = subprocess.run(args, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, check=True)
        stdout, stderr = p.stdout.decode(encoding), p.stderr.decode(encoding)
    else:
        subprocess.check_call(args)
        stdout, stderr = "", ""
    return stdout, stderr


def get_page_count(filename: str) -> int:
    require(PDFTK, "try 'sudo apt install pdftk'")
    stdout, _ = run([PDFTK, filename, "dump_data"], get_output=True)
    regex = re.compile("^NumberOfPages: (\d+)$")
    for line in stdout.splitlines():
        m = regex.match(line)
        if m:
            return int(m.group(1))
    raise ValueError("Can't get PDF page count for: {!r}".format(filename))


# def make_blank_pdf(filename: str, paper: str = "A4") -> None:
#     # https://unix.stackexchange.com/questions/277892/how-do-i-create-a-blank-pdf-from-the-command-line  # noqa
#     require(CONVERT, "try 'sudo apt install imagemagick'")
#     run([CONVERT, "xc:none", "-page", paper, filename])


def convert_to_foldable(input_filename: str,
                        output_filename: str,
                        slice_horiz: int,
                        slice_vert: int,
                        overwrite: bool = False,
                        paper: str = "a4paper") -> bool:
    require(MUTOOL, "try 'sudo apt install mupdf-tools'")
    require(PDFJAM, "try 'sudo apt install pdfjam'")
    if not os.path.isfile(input_filename):
        log.warning("Input file does not exist or is not a file")
        return False
    if not overwrite and os.path.isfile(output_filename):
        log.error("Output file exists; not authorized to overwrite")
        return False
    log.info("Processing {!r}", input_filename)
    with tempfile.TemporaryDirectory() as tmpdir:
        log.debug("Using temporary directory {!r}", tmpdir)

        # Convert to "one real page per PDF page"
        if slice_horiz != 1 or slice_vert != 1:
            log.info("Slicing into {} horizontally x {} vertically",
                     slice_horiz, slice_vert)
            intermediate = os.path.join(tmpdir, "intermediate.pdf")
            # intermediate = os.path.expanduser("~/intermediate.pdf")
            run([
                MUTOOL,
                "poster",
                "-x", str(slice_horiz),
                "-y", str(slice_vert),
                input_filename,
                intermediate
            ])
            input_filename = intermediate

        # Make the final n-up
        n_pages = get_page_count(input_filename)
        n_sheets = calc_n_sheets(n_pages)
        log.info("{} pages -> {} sheets", n_pages, n_sheets)
        pagenums = page_sequence(n_sheets, one_based=True)
        pagespeclist = [str(p) if p <= n_pages else "{}"
                        for p in pagenums]
        # ... switches empty pages to "{}", which is pdfjam notation for
        # an empty page.
        pagespec = ",".join(pagespeclist)

        args = [
            PDFJAM,
            "--paper", paper,
            "--landscape",
            "--nup", "2x1",
            "--keepinfo",
            "--outfile", output_filename,
            "--no-tidy",
            "--",  # "no more options"
            input_filename, pagespec
        ]
        run(args)

    return True


# =============================================================================
# Unit testing
# =============================================================================

class TestPdfToBooklet(unittest.TestCase):
    def test_sequence(self) -> None:
        for n_sheets in range(1, 8 + 1):
            log.info("{!r}", page_sequence(n_sheets=n_sheets, one_based=True))


# =============================================================================
# main
# =============================================================================

def main() -> None:
    main_only_quicksetup_rootlogger(level=logging.DEBUG)
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "input_file",
        help="Input PDF (which is not modified by this program)")
    parser.add_argument(
        "output_file",
        help="Output PDF")
    parser.add_argument(
        "--slice_horiz", type=int, default=1,
        help="Slice the input PDF first into this many parts horizontally")
    parser.add_argument(
        "--slice_vert", type=int, default=1,
        help="Slice the input PDF first into this many parts vertically")
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Allow overwriting of an existing output file")
    parser.add_argument(
        "--unittest", action="store_true",
        help="Run unit tests and exit")
    args = parser.parse_args()

    if args.unittest:
        unittest.main()
        sys.exit(0)

    success = convert_to_foldable(
        input_filename=os.path.abspath(args.input_file),
        output_filename=os.path.abspath(args.output_file),
        slice_horiz=args.slice_horiz,
        slice_vert=args.slice_vert,
        overwrite=args.overwrite
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
