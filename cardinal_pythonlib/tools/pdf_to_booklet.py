#!/usr/bin/env python
# cardinal_pythonlib/tools/pdf_to_booklet.py

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

**Command-line tool to make booklets from PDFs.**

RNC, 18 Nov 2017.

PURPOSE:

Take a PDF created with pdfnup or similar, with A4 sheets and two pages per
sheet, like this:

.. code-block:: none

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

.. code-block:: none

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

- page = one side of a piece of paper BUT HERE, IN A BOOK CONTEXT, half that,
  i.e. what ends up as a book "page"
- pair = two pages, making up one side of a sheet/leaf
- sheet = one piece of paper (= leaf) (= 4 pages, here)

PRINTING

It's our job here to make pairs from pages, and to create a PDF where each
PDF page is a pair.

It's the printer's job to make sheets from pages. When printing in duplex,
you will need to use SHORT-EDGE BINDING (if you use long-edge binding, the
reverse sides will be inverted).

FURTHER THOUGHT 19 Nov 2017

We can, of course, support LONG-EDGE binding as well; that just requires
an extra step of rotating all the even-numbered pages from the preceding
step. Supported, as below.

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

HELP_MISSING_IMAGEMAGICK = "Try 'sudo apt install imagemagick'"
HELP_MISSING_MUTOOL = "Try 'sudo apt install mupdf-tools'"
HELP_MISSING_PDFJAM = "Try 'sudo apt install pdfjam'"
HELP_MISSING_PDFTK = "Try 'sudo apt install pdftk'"

LATEX_PAPER_SIZE_A4 = "a4paper"

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


# =============================================================================
# Calculate page sequence
# =============================================================================

def calc_n_sheets(n_pages: int) -> int:
    """
    How many sheets does this number of pages need, on the basis of 2 pages
    per sheet?
    """
    # NB PyCharm's type checker seems to think math.ceil() returns a float,
    # but it returns an int.
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
    log.debug("{} sheets => page sequence {!r}", n_sheets, sequence)
    return sequence


# =============================================================================
# PDF processor
# =============================================================================

def require(executable: str, explanation: str = "") -> None:
    """
    Ensures that the external tool is available.
    Asserts upon failure.
    """
    assert shutil.which(executable), "Need {!r} on the PATH.{}".format(
        executable, "\n" + explanation if explanation else "")


def run(args: List[str],
        get_output: bool = False,
        encoding: str = sys.getdefaultencoding()) -> Tuple[str, str]:
    """
    Run an external command +/- return the results.
    Returns a ``(stdout, stderr)`` tuple (both are blank strings if the output
    wasn't wanted).
    """
    printable = " ".join(shlex.quote(x) for x in args).replace("\n", r"\n")
    log.debug("Running external command: {}", printable)
    if get_output:
        p = subprocess.run(args, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, check=True)
        stdout, stderr = p.stdout.decode(encoding), p.stderr.decode(encoding)
    else:
        subprocess.check_call(args)
        stdout, stderr = "", ""
    return stdout, stderr


def get_page_count(filename: str) -> int:
    """
    How many pages are in a PDF?
    """
    log.debug("Getting page count for {!r}", filename)
    require(PDFTK, HELP_MISSING_PDFTK)
    stdout, _ = run([PDFTK, filename, "dump_data"], get_output=True)
    regex = re.compile("^NumberOfPages: (\d+)$", re.MULTILINE)
    m = regex.search(stdout)
    if m:
        return int(m.group(1))
    raise ValueError("Can't get PDF page count for: {!r}".format(filename))


def make_blank_pdf(filename: str, paper: str = "A4") -> None:
    """
    NOT USED.
    Makes a blank single-page PDF, using ImageMagick's ``convert``.
    """
    # https://unix.stackexchange.com/questions/277892/how-do-i-create-a-blank-pdf-from-the-command-line  # noqa
    require(CONVERT, HELP_MISSING_IMAGEMAGICK)
    run([CONVERT, "xc:none", "-page", paper, filename])


def slice_pdf(input_filename: str, output_filename: str,
              slice_horiz: int, slice_vert: int) -> str:
    """
    Slice each page of the original, to convert to "one real page per PDF
    page". Return the output filename.
    """
    if slice_horiz == 1 and slice_vert == 1:
        log.debug("No slicing required")
        return input_filename  # nothing to do
    log.info("Slicing each source page mv into {} horizontally x {} vertically",
             slice_horiz, slice_vert)
    log.debug("... from {!r} to {!r}", input_filename, output_filename)
    require(MUTOOL, HELP_MISSING_MUTOOL)
    run([
        MUTOOL,
        "poster",
        "-x", str(slice_horiz),
        "-y", str(slice_vert),
        input_filename,
        output_filename
    ])
    return output_filename


def booklet_nup_pdf(input_filename: str, output_filename: str,
                    latex_paper_size: str = LATEX_PAPER_SIZE_A4) -> str:
    """
    Takes a PDF (e.g. A4) and makes a 2x1 booklet (e.g. 2xA5 per A4).
    The booklet can be folded like a book and the final pages will be in order.
    Returns the output filename.
    """
    log.info("Creating booklet")
    log.debug("... {!r} -> {!r}", input_filename, output_filename)
    require(PDFJAM, HELP_MISSING_PDFJAM)
    n_pages = get_page_count(input_filename)
    n_sheets = calc_n_sheets(n_pages)
    log.debug("{} pages => {} sheets", n_pages, n_sheets)
    pagenums = page_sequence(n_sheets, one_based=True)
    pagespeclist = [str(p) if p <= n_pages else "{}"
                    for p in pagenums]
    # ... switches empty pages to "{}", which is pdfjam notation for
    # an empty page.
    pagespec = ",".join(pagespeclist)
    pdfjam_tidy = True  # clean up after yourself?
    args = [
        PDFJAM,
        "--paper", latex_paper_size,
        "--landscape",
        "--nup", "2x1",
        "--keepinfo",  # e.g. author information
        "--outfile", output_filename,
        "--tidy" if pdfjam_tidy else "--no-tidy",
        "--",  # "no more options"
        input_filename, pagespec
    ]
    run(args)
    return output_filename


def rotate_even_pages_180(input_filename: str, output_filename: str) -> str:
    """
    Rotates even-numbered pages 180 degrees.
    Returns the output filename.
    """
    log.info("Rotating even-numbered pages 180 degrees for long-edge "
             "duplex printing")
    log.debug("... {!r} -> {!r}", input_filename, output_filename)
    require(PDFTK, HELP_MISSING_PDFTK)
    args = [
        PDFTK,
        "A=" + input_filename,  # give it handle 'A'
        # handles are one or more UPPER CASE letters
        "shuffle",
        "Aoddnorth",  # for 'A', keep odd pages as they are
        "Aevensouth",  # for 'A', rotate even pages 180 degrees
        "output", output_filename,
    ]
    run(args)
    return output_filename


def convert_to_foldable(input_filename: str,
                        output_filename: str,
                        slice_horiz: int,
                        slice_vert: int,
                        overwrite: bool = False,
                        longedge: bool = False,
                        latex_paper_size: str = LATEX_PAPER_SIZE_A4) -> bool:
    """
    Runs a chain of tasks to convert a PDF to a useful booklet PDF.
    """
    if not os.path.isfile(input_filename):
        log.warning("Input file does not exist or is not a file")
        return False
    if not overwrite and os.path.isfile(output_filename):
        log.error("Output file exists; not authorized to overwrite (use "
                  "--overwrite if you are sure)")
        return False
    log.info("Processing {!r}", input_filename)
    with tempfile.TemporaryDirectory() as tmpdir:
        log.debug("Using temporary directory {!r}", tmpdir)
        intermediate_num = 0

        def make_intermediate() -> str:
            nonlocal intermediate_num
            intermediate_num += 1
            return os.path.join(tmpdir,
                                "intermediate_{}.pdf".format(intermediate_num))

        # Run this as a chain, rewriting input_filename at each step:
        # Slice, if necessary.
        input_filename = slice_pdf(
            input_filename=input_filename,
            output_filename=make_intermediate(),
            slice_horiz=slice_horiz,
            slice_vert=slice_vert
        )
        # Make the final n-up
        input_filename = booklet_nup_pdf(
            input_filename=input_filename,
            output_filename=make_intermediate(),
            latex_paper_size=latex_paper_size
        )
        # Rotate?
        if longedge:
            input_filename = rotate_even_pages_180(
                input_filename=input_filename,
                output_filename=make_intermediate(),
            )
        # Done.
        log.info("Writing to {!r}", output_filename)
        shutil.move(input_filename, output_filename)
    return True


# =============================================================================
# Unit testing
# =============================================================================

class TestPdfToBooklet(unittest.TestCase):
    """
    Unit tests.
    """
    def test_sequence(self) -> None:
        for n_sheets in range(1, 8 + 1):
            log.info("{!r}", page_sequence(n_sheets=n_sheets, one_based=True))


# =============================================================================
# main
# =============================================================================

def main() -> None:
    """
    Command-line processor. See ``--help`` for details.
    """
    main_only_quicksetup_rootlogger(level=logging.DEBUG)
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
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
        "--longedge", action="store_true",
        help="Create PDF for long-edge duplex printing, not short edge")
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Allow overwriting of an existing output file")
    parser.add_argument(
        "--unittest", action="store_true",
        help="Run unit tests and exit (you must pass dummy values for "
             "input/output files to use these tests)")
    # ... because requiring dummy input/output filenames for unit testing
    # is less confusing for the majority of users than showing syntax in
    # which they are optional!
    args = parser.parse_args()

    if args.unittest:
        log.warning("Performing unit tests")
        # unittest.main() doesn't play nicely with argparse; they both
        # use sys.argv by default (and we end up with what looks like garbage
        # from the argparse help facility); but this works:
        unittest.main(argv=[sys.argv[0]])
        sys.exit(EXIT_SUCCESS)

    success = convert_to_foldable(
        input_filename=os.path.abspath(args.input_file),
        output_filename=os.path.abspath(args.output_file),
        slice_horiz=args.slice_horiz,
        slice_vert=args.slice_vert,
        overwrite=args.overwrite,
        longedge=args.longedge
    )
    sys.exit(EXIT_SUCCESS if success else EXIT_FAILURE)


if __name__ == "__main__":
    main()
