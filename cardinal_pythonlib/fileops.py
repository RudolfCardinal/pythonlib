#!/usr/bin/env python
# cardinal_pythonlib/ui.py

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

File operations.

"""

import fnmatch
import glob
import logging
import os
import shutil
from typing import List

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def mkdir_p(path: str) -> None:
    log.debug("mkdir_p: " + path)
    os.makedirs(path, exist_ok=True)


def copyglob(src: str, dest: str, allow_nothing: bool = False) -> None:
    something = False
    for filename in glob.glob(src):
        shutil.copy(filename, dest)
        something = True
    if something or allow_nothing:
        return
    raise ValueError("No files found matching: {}".format(src))


def copytree(src_dir: str, dest_parent: str) -> None:
    dirname = os.path.basename(os.path.normpath(src_dir))
    dest_dir = os.path.join(dest_parent, dirname)
    shutil.copytree(src_dir, dest_dir)


def chown_r(path: str, user: str, group: str) -> None:
    # http://stackoverflow.com/questions/2853723
    for root, dirs, files in os.walk(path):
        for x in dirs:
            shutil.chown(os.path.join(root, x), user, group)
        for x in files:
            shutil.chown(os.path.join(root, x), user, group)


def moveglob(src: str, dest: str, allow_nothing: bool = False) -> None:
    something = False
    for filename in glob.glob(src):
        shutil.move(filename, dest)
        something = True
    if something or allow_nothing:
        return
    raise ValueError("No files found matching: {}".format(src))


def rmglob(pattern: str) -> None:
    for f in glob.glob(pattern):
        os.remove(f)


def purge(path: str, pattern: str) -> None:
    for f in find(pattern, path):
        log.info("Deleting {}".format(f))
        os.remove(f)


def find(pattern: str, path: str) -> List[str]:
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result


def find_first(pattern, path):
    try:
        return find(pattern, path)[0]
    except IndexError:
        log.critical('''Couldn't find "{}" in "{}"'''.format(pattern, path))
        raise
