#!/usr/bin/env python3
# cardinal_pythonlib/openxml/find_recovered_openxml.py

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

**Tool to recognize and rescue Microsoft Office OpenXML files, even if they
have garbage appended to them. See the command-line help for details.**

Version history:

- Written 28 Sep 2017.

Notes:

- use the ``vbindiff`` tool to show *how* two binary files differ.

Output from ``zip -FF bad.zip --out good.zip``

.. code-block:: none

    Fix archive (-FF) - salvage what can
        zip warning: Missing end (EOCDR) signature - either this archive
                         is not readable or the end is damaged
    Is this a single-disk archive?  (y/n):

... and note there are some tabs in that, too.

More ``zip -FF`` output:

.. code-block:: none

    Fix archive (-FF) - salvage what can
     Found end record (EOCDR) - says expect 50828 splits
      Found archive comment
    Scanning for entries...


    Could not find:
      /home/rudolf/tmp/ziptest/00008470.z01

    Hit c      (change path to where this split file is)
        s      (skip this split)
        q      (abort archive - quit)
        e      (end this archive - no more splits)
        z      (look for .zip split - the last split)
     or ENTER  (try reading this split again):


More ``zip -FF`` output:

.. code-block:: none

    zip: malloc.c:2394: sysmalloc: ...

... this heralds a crash in ``zip``. We need to kill it; otherwise it just sits
there doing nothing and not asking for any input. Presumably this means the
file is badly corrupted (or not a zip at all).

"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import fnmatch
import logging
import multiprocessing
import os
import re
import shutil
import struct
import tempfile
from time import sleep
import traceback
from typing import List
from zipfile import BadZipFile, ZipFile

from cardinal_pythonlib.logs import (
    BraceStyleAdapter,
    main_only_quicksetup_rootlogger,
)
from cardinal_pythonlib.fileops import exists_locked, gen_filenames
from cardinal_pythonlib.subproc import (
    mimic_user_input,
    SOURCE_STDERR,
    SOURCE_STDOUT,
    TERMINATE_SUBPROCESS,
)

log = BraceStyleAdapter(logging.getLogger(__name__))

DOCX_CONTENTS_REGEX_STR = "word/.*xml"
PPTX_CONTENTS_REGEX_STR = "ppt/.*xml"
XLSX_CONTENTS_REGEX_STR = "xl/.*xml"

DOCX_CONTENTS_REGEX = re.compile(DOCX_CONTENTS_REGEX_STR)
PPTX_CONTENTS_REGEX = re.compile(PPTX_CONTENTS_REGEX_STR)
XLSX_CONTENTS_REGEX = re.compile(XLSX_CONTENTS_REGEX_STR)

DOCX = "docx"
PPTX = "pptx"
XLSX = "xlsx"
FILETYPES = [DOCX, PPTX, XLSX]

ZIP_PROMPTS_RESPONSES = [
    (SOURCE_STDOUT, "Is this a single-disk archive?  (y/n): ", "y\n"),
    (SOURCE_STDOUT, " or ENTER  (try reading this split again): ", "q\n"),
    (SOURCE_STDERR,
     "zip: malloc.c:2394: sysmalloc: Assertion `(old_top == initial_top (av) "
     "&& old_size == 0) || ((unsigned long) (old_size) >= MINSIZE && "
     "prev_inuse (old_top) && ((unsigned long) old_end & (pagesize - 1)) "
     "== 0)' failed.", TERMINATE_SUBPROCESS),
]
ZIP_STDOUT_TERMINATORS = ["\n", "): "]


class CorruptedZipReader(object):
    """
    Class to open a zip file, even one that is corrupted, and detect the
    files within.
    """
    def __init__(self, filename: str, show_zip_output: bool = False) -> None:
        """
        Args:
            filename: filename of the ``.zip`` file (or corrupted ``.zip``
                file) to open
            show_zip_output: show the output of the external ``zip`` tool?
        """
        self.src_filename = filename
        self.rescue_filename = ""
        self.tmp_dir = ""
        self.contents_filenames = []  # type: List[str]

        try:
            # A happy zip file will be readable like this:
            with ZipFile(self.src_filename, 'r') as zip_ref:
                self.contents_filenames = zip_ref.namelist()
        except (BadZipFile, OSError) as e:
            # Here we have an unhappy zip file.
            log.debug("File {!r} raised error: {!r}", filename, e)
            self._fix_zip(show_zip_output=show_zip_output)
            try:
                with ZipFile(self.rescue_filename, 'r') as zip_ref:
                    self.contents_filenames = zip_ref.namelist()
            except (BadZipFile, OSError, struct.error) as e:
                log.debug("... exception raised even after fix attempt: {!r}",
                          e)
            if self.contents_filenames:
                log.debug("... recovered!")
            else:
                log.debug("... attempt at recovery failed")

    def _fix_zip(self, show_zip_output: bool = False) -> None:
            # We are trying to deal with ZIP (specifically, PPTX) files that
            # have been retrieved by Scalpel so have large extra bits of junk
            # on the end.
            # Make a file in a temporary directory
            self.tmp_dir = tempfile.mkdtemp()
            self.rescue_filename = os.path.join(
                self.tmp_dir, os.path.basename(self.src_filename))
            cmdargs = [
                "zip",  # Linux zip tool
                "-FF",  # or "--fixfix": "fix very broken things"
                self.src_filename,  # input file
                "--temp-path", self.tmp_dir,  # temporary storage path
                "--out", self.rescue_filename  # output file
            ]
            # We would like to be able to say "y" automatically to
            # "Is this a single-disk archive?  (y/n):"
            # The source code (api.c, zip.c, zipfile.c), from
            # ftp://ftp.info-zip.org/pub/infozip/src/ , suggests that "-q"
            # should do this (internally "-q" sets "noisy = 0") - but in
            # practice it doesn't work. This is a critical switch.
            # Therefore we will do something very ugly, and send raw text via
            # stdin.
            log.debug("Running {!r}", cmdargs)
            mimic_user_input(cmdargs,
                             source_challenge_response=ZIP_PROMPTS_RESPONSES,
                             line_terminators=ZIP_STDOUT_TERMINATORS,
                             print_stdout=show_zip_output,
                             print_stdin=show_zip_output)
            # ... will raise if the 'zip' tool isn't available

    def move_to(self, destination_filename: str,
                alter_if_clash: bool = True) -> None:
        """
        Move the file to which this class refers to a new location.
        The function will not overwrite existing files (but offers the option
        to rename files slightly to avoid a clash).

        Args:
            destination_filename: filename to move to
            alter_if_clash: if ``True`` (the default), appends numbers to
                the filename if the destination already exists, so that the
                move can proceed.
        """
        if not self.src_filename:
            return
        if alter_if_clash:
            counter = 0
            while os.path.exists(destination_filename):
                root, ext = os.path.splitext(destination_filename)
                destination_filename = "{r}_{c}{e}".format(
                    r=root, c=counter, e=ext)
                counter += 1
            # ... for example, "/a/b/c.txt" becomes "/a/b/c_0.txt", then
            # "/a/b/c_1.txt", and so on.
        else:
            if os.path.exists(destination_filename):
                src = self.rescue_filename or self.src_filename
                log.warning("Destination exists; won't move {!r} to {!r}",
                            src, destination_filename)
                return
        if self.rescue_filename:
            shutil.move(self.rescue_filename, destination_filename)
            os.remove(self.src_filename)
            log.info("Moved recovered file {!r} to {!r} and deleted corrupted "
                     "original {!r}",
                     self.rescue_filename,
                     destination_filename,
                     self.src_filename)
            self.rescue_filename = ""
        else:
            shutil.move(self.src_filename, destination_filename)
            log.info("Moved {!r} to {!r}", self.src_filename,
                     destination_filename)
        self.src_filename = ""

    def __del__(self) -> None:
        if self.tmp_dir:
            shutil.rmtree(self.tmp_dir)


class CorruptedOpenXmlReader(CorruptedZipReader):
    """
    Class to read a potentially corrupted OpenXML file.
    As it is created, it sets its ``file_type`` member to the detected OpenXML
    file type, if it can.
    """
    def __init__(self, filename: str, show_zip_output: bool = False) -> None:
        super().__init__(filename=filename,
                         show_zip_output=show_zip_output)
        self.file_type = ""
        self._recognize()

    def _recognize(self) -> None:
        for fname in self.contents_filenames:
            if DOCX_CONTENTS_REGEX.match(fname):
                log.debug("Zip file {!r} has Word DOCX contents {!r}",
                          self.src_filename, fname)
                self.file_type = DOCX
                return
            if PPTX_CONTENTS_REGEX.match(fname):
                log.debug("Zip file {!r} has Powerpoint PPTX contents {!r}",
                          self.src_filename, fname)
                self.file_type = PPTX
                return
            if XLSX_CONTENTS_REGEX.match(fname):
                log.debug("Zip file {!r} has Excel XLSX contents {!r}",
                          self.src_filename, fname)
                self.file_type = XLSX
                return

    def suggested_extension(self) -> str:
        if not self.file_type:
            return ""
        return "." + self.file_type

    @property
    def recognized(self) -> bool:
        return bool(self.file_type)

    @property
    def description(self) -> str:
        return self.file_type.upper()


def process_file(filename: str,
                 filetypes: List[str],
                 move_to: str,
                 delete_if_not_specified_file_type: bool,
                 show_zip_output: bool) -> None:
    """
    Deals with an OpenXML, including if it is potentially corrupted.

    Args:
        filename: filename to process
        filetypes: list of filetypes that we care about, e.g.
            ``['docx', 'pptx', 'xlsx']``.
        move_to: move matching files to this directory
        delete_if_not_specified_file_type: if ``True``, and the file is **not**
            a type specified in ``filetypes``, then delete the file.
        show_zip_output: show the output from the external ``zip`` tool?
    """
    # log.critical("process_file: start")
    try:
        reader = CorruptedOpenXmlReader(filename,
                                        show_zip_output=show_zip_output)
        if reader.file_type in filetypes:
            log.info("Found {}: {}", reader.description, filename)
            if move_to:
                dest_file = os.path.join(move_to, os.path.basename(filename))
                _, ext = os.path.splitext(dest_file)
                if ext != reader.suggested_extension():
                    dest_file += reader.suggested_extension()
                reader.move_to(destination_filename=dest_file)
        else:
            log.info("Unrecognized or unwanted contents: " + filename)
            if delete_if_not_specified_file_type:
                log.info("Deleting: " + filename)
                os.remove(filename)
    except Exception as e:
        # Must explicitly catch and report errors, since otherwise they vanish
        # into the ether.
        log.critical("Uncaught error in subprocess: {!r}\n{}", e,
                     traceback.format_exc())
        raise
        # See also good advice, not implemented here, at
        # https://stackoverflow.com/questions/19924104/python-multiprocessing-handling-child-errors-in-parent  # noqa
        # https://stackoverflow.com/questions/6126007/python-getting-a-traceback-from-a-multiprocessing-process/26096355#26096355  # noqa
    # log.critical("process_file: end")


def main() -> None:
    """
    Command-line handler for the ``find_recovered_openxml`` tool.
    Use the ``--help`` option for help.
    """
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description="""
Tool to recognize and rescue Microsoft Office OpenXML files, even if they have
garbage appended to them.        

- Rationale: when you have accidentally deleted files from an NTFS disk, and
  they really matter, you should (a) stop what you're doing; (b) clone the disk
  to an image file using "dd" under Linux; (c) perform all subsequent 
  operations on the cloned image (in read-only mode). Those steps might 
  include:
    - ntfsundelete, to find files that the filesystem is still aware of;
    - scalpel, to find files based on their contents.

- Scalpel is great at finding stuff efficiently, but it works best when files
  can be defined by both a start (header) signature and an end (footer)
  signature. However, the Microsoft Office OpenXML file format has a 
  recognizable header, but no standard footer. In these circumstances, Scalpel
  reads up to a certain limit that you specify in its configuration file. (To
  retrieve large Powerpoint files, this limit needs to be substantial, e.g.
  50 Mb or more, depending on your ways of working with Powerpoint.)

- That means that files emerging from a Scalpel search for DOCX/PPTX/XLSX files
  may be
    - false positives, having nothing to do with Office;
    - clean Office files (the least likely category!);
    - Office files with garbage stuck on the end.
    
- The OpenXML file format is just a zip file. If you stick too much garbage on
  the end of a zip file, zip readers will see it as corrupt.  
        
- THIS TOOL detects (and optionally moves) potentially corrupted zipfiles based 
  on file contents, by unzipping the file and checking for "inner" files with
  names like:

        File type       Contents filename signature (regular expression)
        ----------------------------------------------------------------
        DOCX            {DOCX_CONTENTS_REGEX_STR}  
        PPTX            {PPTX_CONTENTS_REGEX_STR}
        XLSX            {XLSX_CONTENTS_REGEX_STR}

- WARNING: it's possible for an OpenXML file to contain more than one of these.
  If so, they may be mis-classified.

- If a file is not immediately readable as a zip, it uses Linux's "zip -FF" to 
  repair zip files with corrupted ends, and tries again.
  
- Having found valid-looking files, you can elect to move them elsewhere.

- As an additional and VERY DANGEROUS operation, you can elect to delete files
  that this tool doesn't recognize. (Why? Because a 450Gb disk might produce
  well in excess of 1.7Tb of candidate files; many will be false positives and
  even the true positives will all be expanded to your file size limit, e.g.
  50 Mb. You may have a problem with available disk space, so running this tool
  regularly allows you to clear up the junk. Use the --run_every option to help 
  with this.)

        """.format(
            DOCX_CONTENTS_REGEX_STR=DOCX_CONTENTS_REGEX_STR,
            PPTX_CONTENTS_REGEX_STR=PPTX_CONTENTS_REGEX_STR,
            XLSX_CONTENTS_REGEX_STR=XLSX_CONTENTS_REGEX_STR,
        )
    )
    parser.add_argument(
        "filename", nargs="+",
        help="File(s) to check. You can also specify directores if you use "
             "--recursive"
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
        "--filetypes", nargs="+", default=FILETYPES,
        help="File types to check. Options: {}".format(FILETYPES)
    )
    parser.add_argument(
        "--move_to",
        help="If the file is recognized as one of the specified file types, "
             "move it to the directory specified here."
    )
    parser.add_argument(
        "--delete_if_not_specified_file_type", action="store_true",
        help="If a file is NOT recognized as one of the specified file types, "
             "delete it. VERY DANGEROUS."
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
    parser.add_argument(
        "--show_zip_output", action="store_true",
        help="Verbose output from the external 'zip' tool"
    )
    args = parser.parse_args()
    main_only_quicksetup_rootlogger(
        level=logging.DEBUG if args.verbose else logging.INFO,
        with_process_id=True
    )

    # Further argument checks
    if args.move_to:
        if not os.path.isdir(args.move_to):
            raise ValueError("Destination directory {!r} is not a "
                             "directory".format(args.move_to))
    if not args.filetypes:
        raise ValueError("No file type to scan for")
    filetypes = [ft.lower() for ft in args.filetypes]
    if any(ft not in FILETYPES for ft in filetypes):
        raise ValueError("Invalid filetypes; choose from {}".format(FILETYPES))
    assert shutil.which("zip"), "Need 'zip' tool!"

    # Repeated scanning loop
    while True:
        log.info("Starting scan.")
        log.info("- Looking for filetypes {}", filetypes)
        log.info("- Scanning files/directories {!r}{}",
                 args.filename,
                 " recursively" if args.recursive else "")
        log.info("- Skipping files matching {!r}", args.skip_files)
        log.info("- Using {} simultaneous processes", args.nprocesses)
        if args.move_to:
            log.info("- Moving target files to " + args.move_to)
        if args.delete_if_not_specified_file_type:
            log.info("- Deleting non-target files.")

        # Iterate through files
        pool = multiprocessing.Pool(processes=args.nprocesses)
        for filename in gen_filenames(starting_filenames=args.filename,
                                      recursive=args.recursive):
            src_basename = os.path.basename(filename)
            if any(fnmatch.fnmatch(src_basename, pattern)
                   for pattern in args.skip_files):
                log.info("Skipping file as ordered: " + filename)
                continue
            exists, locked = exists_locked(filename)
            if locked or not exists:
                log.info("Skipping currently inaccessible file: " + filename)
                continue
            kwargs = {
                'filename': filename,
                'filetypes': filetypes,
                'move_to': args.move_to,
                'delete_if_not_specified_file_type':
                    args.delete_if_not_specified_file_type,
                'show_zip_output': args.show_zip_output,
            }
            # log.critical("start")
            pool.apply_async(process_file, [], kwargs)
            # result = pool.apply_async(process_file, [], kwargs)
            # result.get()  # will re-raise any child exceptions
            # ... but it waits for the process to complete! That's no help.
            # log.critical("next")
            # ... https://stackoverflow.com/questions/22094852/how-to-catch-exceptions-in-workers-in-multiprocessing  # noqa
        pool.close()
        pool.join()

        log.info("Finished scan.")
        if args.run_repeatedly is None:
            break
        log.info("Sleeping for {} s...", args.run_repeatedly)
        sleep(args.run_repeatedly)


if __name__ == '__main__':
    main()
