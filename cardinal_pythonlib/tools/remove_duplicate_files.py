#!/usr/bin/env python3
# cardinal_pythonlib/tools/remove_duplicate_files.py

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

**Command-line tool to remove duplicate files from a path.**

Largely based on
http://code.activestate.com/recipes/362459-dupinator-detect-and-delete-duplicate-files/  # noqa

"""

from argparse import ArgumentParser
from hashlib import md5
import logging
import os
from pprint import pformat
import stat
from time import sleep
from typing import Dict, List, Union

from cardinal_pythonlib.fileops import gen_filenames
from cardinal_pythonlib.logs import (
    BraceStyleAdapter,
    main_only_quicksetup_rootlogger,
)

log = BraceStyleAdapter(logging.getLogger(__name__))

INITIAL_HASH_SIZE = 1024
MAIN_READ_CHUNK_SIZE = 4096


def deduplicate(directories: List[str], recursive: bool,
                dummy_run: bool) -> None:
    """
    De-duplicate files within one or more directories. Remove files
    that are identical to ones already considered.

    Args:
        directories: list of directories to process
        recursive: process subdirectories (recursively)?
        dummy_run: say what it'll do, but don't do it
    """
    # -------------------------------------------------------------------------
    # Catalogue files by their size
    # -------------------------------------------------------------------------
    files_by_size = {}  # type: Dict[int, List[str]]  # maps size to list of filenames  # noqa
    num_considered = 0
    for filename in gen_filenames(directories, recursive=recursive):
        if not os.path.isfile(filename):
            continue
        size = os.stat(filename)[stat.ST_SIZE]
        a = files_by_size.setdefault(size, [])
        a.append(filename)
        num_considered += 1

    log.debug("files_by_size =\n{}", pformat(files_by_size))

    # -------------------------------------------------------------------------
    # By size, look for duplicates using a hash of the first part only
    # -------------------------------------------------------------------------
    log.info("Finding potential duplicates...")
    potential_duplicate_sets = []
    potential_count = 0
    sizes = list(files_by_size.keys())
    sizes.sort()
    for k in sizes:
        files_of_this_size = files_by_size[k]
        out_files = []  # type: List[str]
        # ... list of all files having >1 file per hash, for this size
        hashes = {}  # type: Dict[str, Union[bool, str]]
        # ... key is a hash; value is either True or a filename
        if len(files_of_this_size) == 1:
            continue
        log.info("Testing {} files of size {}...", len(files_of_this_size), k)
        for filename in files_of_this_size:
            if not os.path.isfile(filename):
                continue
            log.debug("Quick-scanning file: {}", filename)
            with open(filename, 'rb') as fd:
                hasher = md5()
                hasher.update(fd.read(INITIAL_HASH_SIZE))
                hash_value = hasher.digest()
                if hash_value in hashes:
                    # We have discovered the SECOND OR SUBSEQUENT hash match.
                    first_file_or_true = hashes[hash_value]
                    if first_file_or_true is not True:
                        # We have discovered the SECOND file;
                        # first_file_or_true contains the name of the FIRST.
                        out_files.append(first_file_or_true)
                        hashes[hash_value] = True
                    out_files.append(filename)
                else:
                    # We have discovered the FIRST file with this hash.
                    hashes[hash_value] = filename
        if out_files:
            potential_duplicate_sets.append(out_files)
            potential_count = potential_count + len(out_files)

    del files_by_size

    log.info("Found {} sets of potential duplicates, based on hashing the "
             "first {} bytes of each...", potential_count, INITIAL_HASH_SIZE)

    log.debug("potential_duplicate_sets =\n{}",
              pformat(potential_duplicate_sets))

    # -------------------------------------------------------------------------
    # Within each set, check for duplicates using a hash of the entire file
    # -------------------------------------------------------------------------
    log.info("Scanning for real duplicates...")

    num_scanned = 0
    num_to_scan = sum(len(one_set) for one_set in potential_duplicate_sets)
    duplicate_sets = []  # type: List[List[str]]
    for one_set in potential_duplicate_sets:
        out_files = []  # type: List[str]
        hashes = {}
        for filename in one_set:
            num_scanned += 1
            log.info("Scanning file [{}/{}]: {}",
                     num_scanned, num_to_scan, filename)
            with open(filename, 'rb') as fd:
                hasher = md5()
                while True:
                    r = fd.read(MAIN_READ_CHUNK_SIZE)
                    if len(r) == 0:
                        break
                    hasher.update(r)
            hash_value = hasher.digest()
            if hash_value in hashes:
                if not out_files:
                    out_files.append(hashes[hash_value])
                out_files.append(filename)
            else:
                hashes[hash_value] = filename
        if len(out_files):
            duplicate_sets.append(out_files)

    log.debug("duplicate_sets = \n{}", pformat(duplicate_sets))

    num_originals = 0
    num_deleted = 0
    for d in duplicate_sets:
        print("Original is: {}".format(d[0]))
        num_originals += 1
        for f in d[1:]:
            if dummy_run:
                print("Would delete: {}".format(f))
            else:
                print("Deleting: {}".format(f))
                os.remove(f)
            num_deleted += 1
        print()

    num_unique = num_considered - (num_originals + num_deleted)
    print(
        "{action} {d} duplicates, leaving {o} originals (and {u} unique files "
        "not touched; {c} files considered in total)".format(
            action="Would delete" if dummy_run else "Deleted",
            d=num_deleted,
            o=num_originals,
            u=num_unique,
            c=num_considered
        )
    )


def main() -> None:
    """
    Command-line processor. See ``--help`` for details.
    """
    parser = ArgumentParser(
        description="Remove duplicate files"
    )
    parser.add_argument(
        "directory", nargs="+",
        help="Files and/or directories to check and remove duplicates from."
    )
    parser.add_argument(
        "--recursive", action="store_true",
        help="Recurse through any directories found"
    )
    parser.add_argument(
        "--dummy_run", action="store_true",
        help="Dummy run only; don't actually delete anything"
    )
    parser.add_argument(
        "--run_repeatedly", type=int,
        help="Run the tool repeatedly with a pause of <run_repeatedly> "
             "seconds between runs. (For this to work well,"
             "you should specify one or more DIRECTORIES in "
             "the 'filename' arguments, not files, and you will need the "
             "--recursive option.)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Verbose output"
    )
    args = parser.parse_args()
    main_only_quicksetup_rootlogger(
        level=logging.DEBUG if args.verbose else logging.INFO)

    while True:
        deduplicate(args.directory,
                    recursive=args.recursive,
                    dummy_run=args.dummy_run)
        if args.run_repeatedly is None:
            break
        log.info("Sleeping for {} s...", args.run_repeatedly)
        sleep(args.run_repeatedly)


if __name__ == '__main__':
    main()
