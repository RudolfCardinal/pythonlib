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
from typing import Any, Callable, Generator, List, Tuple

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def mkdir_p(path: str) -> None:
    """
    Makes a directory, and any intermediate (parent) directories if required.
    """
    log.debug("mkdir_p: " + path)
    os.makedirs(path, exist_ok=True)


def copyglob(src: str, dest: str, allow_nothing: bool = False,
             allow_nonfiles: bool = False) -> None:
    """
    Copies files whose filenames match the glob "src" into the directory
    "dest". Raises an error if no files are copied, unless allow_nothing is
    True.
    """
    something = False
    for filename in glob.glob(src):
        if allow_nonfiles or os.path.isfile(filename):
            shutil.copy(filename, dest)
            something = True
    if something or allow_nothing:
        return
    raise ValueError("No files found matching: {}".format(src))


def moveglob(src: str, dest: str, allow_nothing: bool = False,
             allow_nonfiles: bool = False) -> None:
    """
    As for copyglob, but moves instead.
    """
    something = False
    for filename in glob.glob(src):
        if allow_nonfiles or os.path.isfile(filename):
            shutil.move(filename, dest)
            something = True
    if something or allow_nothing:
        return
    raise ValueError("No files found matching: {}".format(src))


def rmglob(pattern: str) -> None:
    """
    Removes all files whose filename matches the glob "pattern".
    """
    for f in glob.glob(pattern):
        os.remove(f)


def copytree(src_dir: str, dest_parent: str) -> None:
    """
    Copies a directory "src_dir" into the directory "dest_parent".
    """
    dirname = os.path.basename(os.path.normpath(src_dir))
    dest_dir = os.path.join(dest_parent, dirname)
    shutil.copytree(src_dir, dest_dir)


def chown_r(path: str, user: str, group: str) -> None:
    """
    Performs a recursive chown.
    """
    # http://stackoverflow.com/questions/2853723
    for root, dirs, files in os.walk(path):
        for x in dirs:
            shutil.chown(os.path.join(root, x), user, group)
        for x in files:
            shutil.chown(os.path.join(root, x), user, group)


def find(pattern: str, path: str) -> List[str]:
    """
    Finds files in "path" whose filenames match "pattern".
    """
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result


def find_first(pattern: str, path: str) -> str:
    """
    Finds first file in "path" whose filename matches "pattern", or raises.
    """
    try:
        return find(pattern, path)[0]
    except IndexError:
        log.critical('''Couldn't find "{}" in "{}"'''.format(pattern, path))
        raise


def purge(path: str, pattern: str) -> None:
    """
    Deletes all files in "path" matching "pattern".
    """
    for f in find(pattern, path):
        log.info("Deleting {}".format(f))
        os.remove(f)


def preserve_cwd(func: Callable) -> Callable:
    """
    Decorator to preserve the current working directory in calls to the
    decorated function.

    Example:

        @preserve_cwd
        def myfunc():
            os.chdir("/faraway")

        os.chdir("/home")
        myfunc()
        assert os.getcwd() == "/home"
    """
    # http://stackoverflow.com/questions/169070/python-how-do-i-write-a-decorator-that-restores-the-cwd  # noqa
    def decorator(*args_, **kwargs) -> Any:
        cwd = os.getcwd()
        result = func(*args_, **kwargs)
        os.chdir(cwd)
        return result
    return decorator


def gen_filenames(starting_filenames: List[str],
                  recursive: bool) -> Generator[str, None, None]:
    for base_filename in starting_filenames:
        if os.path.isfile(base_filename):
            yield os.path.abspath(base_filename)
        elif os.path.isdir(base_filename) and recursive:
            for dirpath, dirnames, filenames in os.walk(base_filename):
                for fname in filenames:
                    yield os.path.abspath(os.path.join(dirpath, fname))


def exists_locked(filepath: str) -> Tuple[bool, bool]:
    """
    Checks if a file is locked by opening it in append mode.
    If no exception thrown, then the file is not locked.
    # https://www.calazan.com/how-to-check-if-a-file-is-locked-in-python/
    """
    exists = False
    locked = None
    file_object = None
    if os.path.exists(filepath):
        exists = True
        locked = True
        try:
            buffer_size = 8
            # Opening file in append mode and read the first 8 characters.
            file_object = open(filepath, 'a', buffer_size)
            if file_object:
                locked = False  # exists and not locked
        except IOError:
            pass
        finally:
            if file_object:
                file_object.close()
    return exists, locked
