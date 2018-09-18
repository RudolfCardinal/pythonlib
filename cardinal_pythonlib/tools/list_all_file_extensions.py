#!/usr/bin/env python
# cardinal_pythonlib/tools/list_all_file_extensions.py

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

**Command-line tool to enumerate all file extensions found within a path.**

"""


import argparse
import logging
import os
from typing import List

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

log = logging.getLogger(__name__)


def list_file_extensions(path: str, reportevery: int = 1) -> List[str]:
    """
    Returns a sorted list of every file extension found in a directory
    and its subdirectories.

    Args:
        path: path to scan
        reportevery: report directory progress after every *n* steps

    Returns:
        sorted list of every file extension found

    """
    extensions = set()
    count = 0
    for root, dirs, files in os.walk(path):
        count += 1
        if count % reportevery == 0:
            log.debug("Walking directory {}: {}".format(count, repr(root)))
        for file in files:
            filename, ext = os.path.splitext(file)
            extensions.add(ext)
    return sorted(list(extensions))


def main() -> None:
    """
    Command-line processor. See ``--help`` for details.
    """
    main_only_quicksetup_rootlogger(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default=os.getcwd())
    parser.add_argument("--reportevery", default=10000)
    args = parser.parse_args()
    log.info("Extensions in directory {}:".format(repr(args.directory)))
    print("\n".join(repr(x) for x in
                    list_file_extensions(args.directory,
                                         reportevery=args.reportevery)))


if __name__ == '__main__':
    main()
