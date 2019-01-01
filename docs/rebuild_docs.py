#!/usr/bin/env python
# cardinal_pythonlib/docs/rebuild_docs.py

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

import os
import shutil
import subprocess
import sys
if sys.version_info[0] < 3:
    raise AssertionError("Need Python 3")

# Work out directories
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
BUILD_HTML_DIR = os.path.join(THIS_DIR, "build", "html")

DEST_DIRS = []

if __name__ == '__main__':
    # Remove anything old
    for destdir in [BUILD_HTML_DIR] + DEST_DIRS:
        print("Deleting directory {!r}".format(destdir))
        shutil.rmtree(destdir, ignore_errors=True)

    # Build docs
    print("Making HTML version of documentation")
    os.chdir(THIS_DIR)
    subprocess.call(["make", "html"])

    # Copy
    for destdir in DEST_DIRS:
        print("Copying {!r} -> {!r}".format(BUILD_HTML_DIR, destdir))
        shutil.copytree(BUILD_HTML_DIR, destdir)
