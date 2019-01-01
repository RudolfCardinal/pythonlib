#!/usr/bin/env python
# cardinal_pythonlib/docs/make_autodoc_rst.py

"""
===============================================================================

    Original code copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).

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
"""

import argparse
import logging
import os

from cardinal_pythonlib.fileops import relative_filename_within_dir
from cardinal_pythonlib.logs import (
    BraceStyleAdapter,
    main_only_quicksetup_rootlogger,
)
from cardinal_pythonlib.sphinxtools import FileToAutodocument

log = BraceStyleAdapter(logging.getLogger(__name__))

THIS_DIR = os.path.dirname(os.path.realpath(__file__))  # .../docs
PACKAGE_ROOT_DIR = os.path.abspath(os.path.join(THIS_DIR, os.pardir))  # .../
AUTODOC_DIR = os.path.join(THIS_DIR, "source", "autodoc")
AUTODOC_INDEX = os.path.join(AUTODOC_DIR, "_index.rst")

COPYRIGHT_COMMENT = r"""
..  Copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).
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


def make_autodoc(filename: str, make: bool, skip_init: bool = True) -> None:
    # Skip "__init__.py" unless we were specifically asked not to:
    basename = os.path.basename(filename)
    if basename == "__init__.py" and skip_init:
        log.info("Skipping {!r}", filename)
        return

    rel_filename = relative_filename_within_dir(
        filename, PACKAGE_ROOT_DIR)
    filename_without_ext = os.path.splitext(rel_filename)[0]
    filename_parts = filename_without_ext.split(os.sep)
    autodoc_parts = filename_parts[1:]
    rst_rel_filename = os.path.join(*autodoc_parts) + ".rst"
    rst_abs_filename = os.path.join(AUTODOC_DIR, rst_rel_filename)

    index_addition = "    " + rst_rel_filename
    log.debug("Index addition: {!r}", index_addition)

    # Represent our files:
    f = FileToAutodocument(
        source_filename=filename,
        project_root_dir=PACKAGE_ROOT_DIR,
        target_rst_filename=rst_abs_filename,
    )
    log.info("Autodocumenting with {!r}", f)

    if make:
        f.write_rst(
            prefix=COPYRIGHT_COMMENT,
            heading_underline_char="~",
            overwrite=False
        )
        log.info("Appending to index file {!r}", AUTODOC_INDEX)
        with open(AUTODOC_INDEX, "a") as indexfile:
            indexfile.write(index_addition + "\n")
        log.info("... written to index successfully")
    else:
        log.info("Show intent only; nothing to do.")


def main() -> None:
    main_only_quicksetup_rootlogger(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filename", type=str, nargs="+",
        help="Filename of Python file to autodocument")
    parser.add_argument(
        "--make", action="store_true",
        help="Add the file! Otherwise will just show its intent.")
    args = parser.parse_args()

    for filename in args.filename:
        make_autodoc(filename, args.make)


if __name__ == '__main__':
    main()
