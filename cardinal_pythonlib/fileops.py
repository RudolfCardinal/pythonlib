#!/usr/bin/env python
# cardinal_pythonlib/ui.py

"""
===============================================================================
    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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

from contextlib import contextmanager
import fnmatch
import glob
import logging
import os
import shutil
import stat
from types import TracebackType
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Find or require executables
# =============================================================================

def which_with_envpath(executable: str, env: Dict[str, str]) -> str:
    """
    Performs a "which" command using the PATH from the specified environment.

    Reason: when you use run([executable, ...], env) and therefore
    subprocess.run([executable, ...], env=env), the PATH that's searched for
    "executable" is the parent's, not the new child's -- so you have to find
    the executable manually.
    """
    oldpath = os.environ.get("PATH", "")
    os.environ["PATH"] = env.get("PATH")
    which = shutil.which(executable)
    os.environ["PATH"] = oldpath
    return which


def require_executable(executable: str) -> None:
    if shutil.which(executable):
        return
    errmsg = "Missing command (must be on the PATH): " + executable
    log.critical(errmsg)
    raise FileNotFoundError(errmsg)


# =============================================================================
# Create directories
# =============================================================================

def mkdir_p(path: str) -> None:
    """
    Makes a directory, and any intermediate (parent) directories if required.
    """
    log.debug("mkdir -p " + path)
    os.makedirs(path, exist_ok=True)


# =============================================================================
# Change directories
# =============================================================================

@contextmanager
def pushd(directory: str) -> None:
    """
    Context manager: changes directory and preserves the original on exit.
    Example:
        with pushd(new_directory):
            # do things
    """
    previous_dir = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(previous_dir)


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


def root_path() -> str:
    """
    Returns the system root directory.
    """
    # http://stackoverflow.com/questions/12041525
    return os.path.abspath(os.sep)


# =============================================================================
# Copy or move things
# =============================================================================

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


def copy_tree_root(src_dir: str, dest_parent: str) -> None:
    """
    Copies a directory "src_dir" into the directory "dest_parent".
    That is:

        /source/thing/a.txt
        /source/thing/b.txt
        /source/thing/somedir/c.txt

        copy_tree_root("/source/thing", "/dest")

    ends up creating

        /dest/thing/a.txt
        /dest/thing/b.txt
        /dest/thing/somedir/c.txt
    """
    dirname = os.path.basename(os.path.normpath(src_dir))
    dest_dir = os.path.join(dest_parent, dirname)
    shutil.copytree(src_dir, dest_dir)


def copy_tree_contents(srcdir: str, destdir: str,
                       destroy: bool = False) -> None:
    """
    Recursive copy. Unlike copy_tree_root, copy_tree_contents works this way:
    with the file structure above,

        copy_tree_contents("/source/thing", "/dest")

    ends up creating:

        /dest/a.txt
        /dest/b.txt
        /dest/somedir/c.txt

    """
    log.info("Copying directory {} -> {}".format(srcdir, destdir))
    if os.path.exists(destdir):
        if not destroy:
            raise ValueError("Destination exists!")
        if not os.path.isdir(destdir):
            raise ValueError("Destination exists but isn't a directory!")
        log.debug("... removing old contents")
        rmtree(destdir)
        log.debug("... now copying")
    shutil.copytree(srcdir, destdir)


# =============================================================================
# Delete things
# =============================================================================

def rmglob(pattern: str) -> None:
    """
    Removes all files whose filename matches the glob "pattern".
    """
    for f in glob.glob(pattern):
        os.remove(f)


def purge(path: str, pattern: str) -> None:
    """
    Deletes all files in "path" matching "pattern".
    """
    for f in find(pattern, path):
        log.info("Deleting {}".format(f))
        os.remove(f)


def delete_files_within_dir(directory: str, filenames: List[str]) -> None:
    """
    Delete files within "directory" whose filename *exactly* matches one of
    "filenames".
    """
    for dirpath, dirnames, fnames in os.walk(directory):
        for f in fnames:
            if f in filenames:
                fullpath = os.path.join(dirpath, f)
                log.debug("Deleting {!r}".format(fullpath))
                os.remove(fullpath)


EXC_INFO_TYPE = Tuple[
    Optional[Any],  # Type[BaseException]], but that's not in Python 3.5
    Optional[BaseException],
    Optional[TracebackType],  # it's a traceback object
]
# https://docs.python.org/3/library/sys.html#sys.exc_info


def shutil_rmtree_onerror(func: Callable[[str], None],
                          path: str,
                          exc_info: EXC_INFO_TYPE) -> None:
    # https://stackoverflow.com/questions/2656322/shutil-rmtree-fails-on-windows-with-access-is-denied  # noqa
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    if not os.access(path, os.W_OK):
        # Is the error an access error ?
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        exc = exc_info[1]
        raise exc


def rmtree(directory: str) -> None:
    """
    Deletes a directory tree.
    """
    log.debug("Deleting directory {}".format(directory))
    shutil.rmtree(directory, onerror=shutil_rmtree_onerror)


# =============================================================================
# Change ownership or permissions
# =============================================================================

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


def chmod_r(root: str, permission: int) -> None:
    # Untested
    # Permission: e.g. stat.S_IWUSR
    os.chmod(root, permission)
    for dirpath, dirnames, filenames in os.walk(root):
        for d in dirnames:
            os.chmod(os.path.join(dirpath, d), permission)
        for f in filenames:
            os.chmod(os.path.join(dirpath, f), permission)


# =============================================================================
# Find files
# =============================================================================

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


def gen_filenames(starting_filenames: List[str],
                  recursive: bool) -> Generator[str, None, None]:
    for base_filename in starting_filenames:
        if os.path.isfile(base_filename):
            yield os.path.abspath(base_filename)
        elif os.path.isdir(base_filename) and recursive:
            for dirpath, dirnames, filenames in os.walk(base_filename):
                for fname in filenames:
                    yield os.path.abspath(os.path.join(dirpath, fname))


# =============================================================================
# Check lock status
# =============================================================================

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
