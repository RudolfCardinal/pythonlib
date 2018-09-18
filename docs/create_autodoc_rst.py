#!/usr/bin/env python
# cardinal_pythonlib/docs/make_autodoc_rst.py

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

Rationale: if you want Sphinx autodoc code to appear as "one module per Sphinx
page", you need one .rst file per module.

"""

import argparse
import logging
import os
import sys

from cardinal_pythonlib.fileops import mkdir_p, relative_filename_within_dir
from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

log = logging.getLogger(__name__)
THIS_DIR = os.path.dirname(os.path.realpath(__file__))  # .../docs  # noqa
PACKAGE_ROOT_DIR = os.path.abspath(os.path.join(THIS_DIR, os.pardir))  # .../
AUTODOC_DIR = os.path.join(THIS_DIR, "source", "autodoc")
AUTODOC_INDEX = os.path.join(AUTODOC_DIR, "_index.rst")

AUTODOC_TEMPLATE = r"""
..  cardinal_pythonlib/docs/source/autodoc/{filename}.rst

..  Copyright © 2009-2018 Rudolf Cardinal (rudolf@pobox.com).
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


{modulename}
{tildes}

.. automodule:: {modulename}
    :members:
"""


def make_autodoc(filename: str, make: bool, skip_init: bool = True) -> None:
    log.info("Python filename: {!r}".format(filename))
    if not os.path.exists(filename):
        log.error("No such Python file: {!r}".format(filename))
        sys.exit(1)

    rel_filename = relative_filename_within_dir(
        filename, PACKAGE_ROOT_DIR)
    if not rel_filename:
        log.error("Filename {!r} is not within directory {!r}".format(
            filename, PACKAGE_ROOT_DIR))
    basename = os.path.basename(rel_filename)
    if basename == "__init__.py" and skip_init:
        log.info("Skipping {!r}".format(filename))
        return
    log.info("Relative to package root: {!r}".format(rel_filename))

    filename_without_ext = os.path.splitext(rel_filename)[0]
    filename_parts = filename_without_ext.split(os.sep)
    module_name = ".".join(filename_parts)
    log.info("Module: {!r}".format(module_name))

    autodoc_parts = filename_parts[1:]
    rst_rel_filename = os.path.join(*autodoc_parts) + ".rst"
    rst_abs_filename = os.path.join(AUTODOC_DIR, rst_rel_filename)
    dest_dir = os.path.dirname(rst_abs_filename)
    autodoc_filename_for_header = os.path.join(*autodoc_parts)
    log.info("Destination filename: {!r}".format(rst_abs_filename))

    contents = AUTODOC_TEMPLATE.format(
        filename=autodoc_filename_for_header,
        modulename=module_name,
        tildes="~" * len(module_name)
    )
    log.debug("Destination directory: {!r}".format(dest_dir))
    log.debug("Contents: \n{}".format(contents))

    index_addition = "    " + rst_rel_filename
    log.debug("Index addition: {!r}".format(index_addition))

    if make:
        if os.path.exists(rst_abs_filename):
            log.error("File already exists, aborting: {!r}".format(
                rst_abs_filename))
            sys.exit(1)
        if not os.path.exists(dest_dir):
            log.info("Making directory: {!r}".format(dest_dir))
            mkdir_p(dest_dir)
        log.info("Writing to {!r}".format(rst_abs_filename))
        with open(rst_abs_filename, "w") as outfile:
            outfile.write(contents)
        log.info("... written successfully")
        log.info("Appending to index file {!r}".format(AUTODOC_INDEX))
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
