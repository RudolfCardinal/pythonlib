#!/usr/bin/env python
# docs/create_all_autodocs.py

"""
..

===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

..
"""

import argparse
import logging
import os
import sys

from cardinal_pythonlib.fileops import rmtree
from cardinal_pythonlib.logs import (
    BraceStyleAdapter,
    main_only_quicksetup_rootlogger,
)
from cardinal_pythonlib.sphinxtools import AutodocIndex, AutodocMethod

if sys.version_info[0] < 3:
    raise AssertionError("Need Python 3")
log = BraceStyleAdapter(logging.getLogger(__name__))

# Work out directories
THIS_DIR = os.path.dirname(os.path.realpath(__file__))  # .../docs
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(THIS_DIR, os.pardir))  # .../
PYTHON_PACKAGE_ROOT_DIR = os.path.join(PROJECT_ROOT_DIR, "cardinal_pythonlib")
CODE_ROOT_DIR = PYTHON_PACKAGE_ROOT_DIR
AUTODOC_DIR = os.path.join(THIS_DIR, "source", "autodoc")
INDEX_FILENAME = "_index.rst"
TOP_AUTODOC_INDEX = os.path.join(AUTODOC_DIR, INDEX_FILENAME)

COPYRIGHT_COMMENT = r"""
..  Copyright (C) 2009-2020 Rudolf Cardinal (rudolf@pobox.com).
    .
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
    .
        http://www.apache.org/licenses/LICENSE-2.0
    .
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""


def make_autodoc(make: bool, destroy_first: bool) -> None:
    if destroy_first:
        if make and os.path.exists(AUTODOC_DIR):
            log.info("Deleting directory {!r}", AUTODOC_DIR)
            rmtree(AUTODOC_DIR)
        else:
            log.warning("Would delete directory {!r} (not doing so as in mock "
                        "mode)", AUTODOC_DIR)
    top_idx = AutodocIndex(
        autodoc_rst_root_dir=AUTODOC_DIR,
        highest_code_dir=CODE_ROOT_DIR,
        index_filename=TOP_AUTODOC_INDEX,
        index_heading_underline_char="-",
        method=AutodocMethod.BEST,
        project_root_dir=PROJECT_ROOT_DIR,
        python_package_root_dir=PROJECT_ROOT_DIR,
        recursive=True,
        rst_prefix=COPYRIGHT_COMMENT,
        source_filenames_or_globs=[
            os.path.join(CODE_ROOT_DIR, "**/*.py"),
        ],
        source_rst_heading_underline_char="~",
        toctree_maxdepth=1,
    )
    top_idx.write_index_and_rst_files(overwrite=True, mock=not make)
    # print(top_idx.index_content())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--make", action="store_true",
        help="Do things! Otherwise will just show its intent.")
    parser.add_argument(
        "--destroy_first", action="store_true",
        help="Destroy all existing autodocs first")
    parser.add_argument(
        "--verbose", action="store_true",
        help="Be verbose")
    args = parser.parse_args()

    main_only_quicksetup_rootlogger(
        level=logging.DEBUG if args.verbose else logging.INFO)

    make_autodoc(make=args.make,
                 destroy_first=args.destroy_first)


if __name__ == '__main__':
    main()
