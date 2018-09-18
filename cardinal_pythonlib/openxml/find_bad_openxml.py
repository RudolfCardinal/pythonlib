#!/usr/bin/env python3
# cardinal_pythonlib/openxml/find_bad_openxml.py

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

**Tool to scan rescued Microsoft Office OpenXML files (produced by the
"find_recovered_openxml.py" tool in this kit; q.v.) and detect bad
(corrupted) ones.**

"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import fnmatch
import logging
import multiprocessing
# from pprint import pformat
import os
from sys import stdin
from time import sleep
import traceback
from typing import Generator, List
from zipfile import BadZipFile, ZipFile, ZipInfo

from cardinal_pythonlib.logs import (
    BraceStyleAdapter,
    main_only_quicksetup_rootlogger,
)
from cardinal_pythonlib.fileops import exists_locked, gen_filenames
from cardinal_pythonlib.openxml.find_recovered_openxml import (
    DOCX_CONTENTS_REGEX,
    PPTX_CONTENTS_REGEX,
    XLSX_CONTENTS_REGEX,
)

log = BraceStyleAdapter(logging.getLogger(__name__))

MANDATORY_FILENAMES = [
    # https://msdn.microsoft.com/en-us/library/aa982683(v=office.12).aspx

    "[Content_Types].xml",

    # "_rels/.rels",
    # ... not strictly mandatory:
    #     https://en.wikipedia.org/wiki/Open_Packaging_Conventions

    # "docProps/core.xml"
    # ... NOT mandatory, or at least I have a .pptx that works fine without it
]

NULL_DATE_TIME = (1980, 1, 1, 0, 0, 0)


def gen_from_stdin() -> Generator[str, None, None]:
    """
    Yields stripped lines from stdin.
    """
    for line in stdin.readlines():
        yield line.strip()


def is_openxml_good(filename: str) -> bool:
    """
    Determines whether an OpenXML file appears to be good (not corrupted).
    """
    try:
        log.debug("Trying: {}", filename)
        with ZipFile(filename, 'r') as zip_ref:
            namelist = zip_ref.namelist()  # type: List[str]
            # log.critical("\n{}", pformat(namelist))
            # -----------------------------------------------------------------
            # Contains key files?
            # -----------------------------------------------------------------
            for mandatory_filename in MANDATORY_FILENAMES:
                if mandatory_filename not in namelist:
                    log.debug("Bad [missing {!r}]: {}",
                              mandatory_filename, filename)
                    return False

            infolist = zip_ref.infolist()  # type: List[ZipInfo]
            contains_docx = False
            contains_pptx = False
            contains_xlsx = False
            for info in infolist:
                # -------------------------------------------------------------
                # Sensible date check?
                # ... NO: lots of perfectly good files have this date/time.
                # -------------------------------------------------------------
                # if info.date_time == NULL_DATE_TIME:
                #     log.debug("{!r}: {!r}", info.filename, info.date_time)

                # -------------------------------------------------------------
                # Only one kind of contents?
                # ... YES, I think so. This has 100% reliability on my
                # stash of 34 PPTX, 223 DOCX, 85 XLSX, and labelled none as bad
                # from an HFC collection of 1866 such files. There are lots of
                # files emerging from Scalpel (plus my find_recovered_openxml
                # zip-fixing tool) that fail this test, though.
                # -------------------------------------------------------------
                if (not contains_docx and
                        DOCX_CONTENTS_REGEX.search(info.filename)):
                    contains_docx = True
                if (not contains_pptx and
                        PPTX_CONTENTS_REGEX.search(info.filename)):
                    contains_pptx = True
                if (not contains_xlsx and
                        XLSX_CONTENTS_REGEX.search(info.filename)):
                    contains_xlsx = True
                if sum([contains_docx, contains_pptx, contains_xlsx]) > 1:
                    log.debug("Bad [>1 of DOCX, PPTX, XLSX content]: {}",
                              filename)
                    return False

            return True
    except (BadZipFile, OSError) as e:
        # ---------------------------------------------------------------------
        # Duff file. Easy!
        # ---------------------------------------------------------------------
        log.debug("Bad [BadZipFile or OSError]: {!r}; error was {!r}",
                  filename, e)
        return False


def process_openxml_file(filename: str,
                         print_good: bool,
                         delete_if_bad: bool) -> None:
    """
    Prints the filename of, or deletes, an OpenXML file depending on whether
    it is corrupt or not.

    Args:
        filename: filename to check
        print_good: if ``True``, then prints the filename if the file
            appears good.
        delete_if_bad: if ``True``, then deletes the file if the file
            appears corrupt.
    """
    print_bad = not print_good
    try:
        file_good = is_openxml_good(filename)
        file_bad = not file_good
        if (print_good and file_good) or (print_bad and file_bad):
            print(filename)
        if delete_if_bad and file_bad:
            log.warning("Deleting: {}", filename)
            os.remove(filename)
    except Exception as e:
        # Must explicitly catch and report errors, since otherwise they vanish
        # into the ether.
        log.critical("Uncaught error in subprocess: {!r}\n{}", e,
                     traceback.format_exc())
        raise


def main() -> None:
    """
    Command-line handler for the ``find_bad_openxml`` tool.
    Use the ``--help`` option for help.
    """
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description="""
Tool to scan rescued Microsoft Office OpenXML files (produced by the
find_recovered_openxml.py tool in this kit; q.v.) and detect bad (corrupted)
ones.
        """
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
    parser.add_argument(
        "--skip_files", nargs="*", default=[],
        help="File pattern(s) to skip. You can specify wildcards like '*.txt' "
             "(but you will have to enclose that pattern in quotes under "
             "UNIX-like operating systems). The basename of each file will be "
             "tested against these filenames/patterns. Consider including "
             "Scalpel's 'audit.txt'."
    )
    parser.add_argument(
        "--good", action="store_true",
        help="List good files, not bad"
    )
    parser.add_argument(
        "--delete_if_bad", action="store_true",
        help="If a file is found to be bad, delete it. DANGEROUS."
    )
    parser.add_argument(
        "--run_repeatedly", type=int,
        help="Run the tool repeatedly with a pause of <run_repeatedly> "
             "seconds between runs. (For this to work well with the move/"
             "delete options, you should specify one or more DIRECTORIES in "
             "the 'filename' arguments, not files, and you will need the "
             "--recursive option.)"
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
        level=logging.DEBUG if args.verbose else logging.INFO,
        with_process_id=True
    )
    if bool(args.filenames_from_stdin) == bool(args.filename):
        raise ValueError("Specify --filenames_from_stdin or filenames on the "
                         "command line, but not both")
    if args.filenames_from_stdin and args.run_repeatedly:
        raise ValueError("Can't use both --filenames_from_stdin and "
                         "--run_repeatedly")

    # Repeated scanning loop
    while True:
        log.debug("Starting scan.")
        log.debug("- Scanning files/directories {!r}{}",
                  args.filename,
                  " recursively" if args.recursive else "")
        log.debug("- Skipping files matching {!r}", args.skip_files)
        log.debug("- Using {} simultaneous processes", args.nprocesses)
        log.debug("- Reporting {} filenames", "good" if args.good else "bad")
        if args.delete_if_bad:
            log.warning("- Deleting bad OpenXML files.")

        # Iterate through files
        pool = multiprocessing.Pool(processes=args.nprocesses)

        if args.filenames_from_stdin:
            generator = gen_from_stdin()
        else:
            generator = gen_filenames(starting_filenames=args.filename,
                                      recursive=args.recursive)

        for filename in generator:
            src_basename = os.path.basename(filename)
            if any(fnmatch.fnmatch(src_basename, pattern)
                   for pattern in args.skip_files):
                log.debug("Skipping file as ordered: " + filename)
                continue
            exists, locked = exists_locked(filename)
            if locked or not exists:
                log.debug("Skipping currently inaccessible file: " + filename)
                continue
            kwargs = {
                'filename': filename,
                'print_good': args.good,
                'delete_if_bad': args.delete_if_bad,
            }
            # log.critical("start")
            pool.apply_async(process_openxml_file, [], kwargs)
            # result = pool.apply_async(process_file, [], kwargs)
            # result.get()  # will re-raise any child exceptions
            # ... but it waits for the process to complete! That's no help.
            # log.critical("next")
            # ... https://stackoverflow.com/questions/22094852/how-to-catch-exceptions-in-workers-in-multiprocessing  # noqa
        pool.close()
        pool.join()

        log.debug("Finished scan.")
        if args.run_repeatedly is None:
            break
        log.info("Sleeping for {} s...", args.run_repeatedly)
        sleep(args.run_repeatedly)


if __name__ == '__main__':
    main()
