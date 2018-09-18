#!/usr/bin/env python
# cardinal_pythonlib/platformfunc.py

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

**Support for platform-specific problems.**
"""

from collections import OrderedDict
import itertools
import logging
from pprint import pformat
import subprocess
import sys
from typing import Any, Dict, Generator, Iterator, List, Tuple, Union

from cardinal_pythonlib.fileops import require_executable

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Fix UTF-8 output problems on Windows
# =============================================================================
# http://stackoverflow.com/questions/5419

def fix_windows_utf8_output() -> None:
    # Python 3 only now, so nothing to do
    return

    # if six.PY3:
    #     return
    # reload_module(sys)
    # # noinspection PyUnresolvedReferences
    # sys.setdefaultencoding('utf-8')
    # # print sys.getdefaultencoding()
    #
    # if sys.platform == 'win32':
    #     try:
    #         import win32console
    #     except ImportError:
    #         win32console = None
    #         print(
    #             "Python Win32 Extensions module is required.\n "
    #             "You can download it from "
    #             "https://sourceforge.net/projects/pywin32/ "
    #             "(x86 and x64 builds are available)\n")
    #         exit(-1)
    #     # win32console implementation  of SetConsoleCP does not return a value
    #     # CP_UTF8 = 65001
    #     win32console.SetConsoleCP(65001)
    #     if win32console.GetConsoleCP() != 65001:
    #         raise RuntimeError("Cannot set console codepage to 65001 (UTF-8)")
    #     win32console.SetConsoleOutputCP(65001)
    #     if win32console.GetConsoleOutputCP() != 65001:
    #         raise RuntimeError("Cannot set console output codepage to 65001 "
    #                            "(UTF-8)")
    #
    # sys.stdout = codecs.getwriter('utf8')(sys.stdout)
    # sys.stderr = codecs.getwriter('utf8')(sys.stderr)
    # # CHECK: does that modify the "global" sys.stdout?
    # # You can't use "global sys.stdout"; that raises an error


def test_windows_utf8_output() -> None:
    """
    Print a short string with unusual Unicode characters.
    """
    print(u"This is an Е乂αmp١ȅ testing Unicode support using Arabic, Latin, "
          u"Cyrillic, Greek, Hebrew and CJK code points.\n")


if __name__ == '__main__':
    fix_windows_utf8_output()
    test_windows_utf8_output()


# =============================================================================
# Check package presence on Debian
# =============================================================================

DPKG_QUERY = "dpkg-query"


def are_debian_packages_installed(packages: List[str]) -> Dict[str, bool]:
    """
    Check which of a list of Debian packages are installed, via ``dpkg-query``.

    Args:
        packages: list of Debian package names

    Returns:
        dict: mapping from package name to boolean ("present?")

    """
    assert len(packages) >= 1
    require_executable(DPKG_QUERY)
    args = [
        DPKG_QUERY,
        "-W",  # --show
        # "-f='${Package} ${Status} ${Version}\n'",
        "-f=${Package} ${Status}\n",  # --showformat
    ] + packages
    completed_process = subprocess.run(args,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       check=False)
    encoding = sys.getdefaultencoding()
    stdout = completed_process.stdout.decode(encoding)
    stderr = completed_process.stderr.decode(encoding)
    present = OrderedDict()
    for line in stdout.split("\n"):
        if line:  # e.g. "autoconf install ok installed"
            words = line.split()
            assert len(words) >= 2
            package = words[0]
            present[package] = "installed" in words[1:]
    for line in stderr.split("\n"):
        if line:  # e.g. "dpkg-query: no packages found matching XXX"
            words = line.split()
            assert len(words) >= 2
            package = words[-1]
            present[package] = False
    log.debug("Debian package presence: {}".format(present))
    return present


def require_debian_packages(packages: List[str]) -> None:
    """
    Ensure specific packages are installed under Debian.

    Args:
        packages: list of packages

    Raises:
        ValueError: if any are missing

    """
    present = are_debian_packages_installed(packages)
    missing_packages = [k for k, v in present.items() if not v]
    if missing_packages:
        missing_packages.sort()
        msg = (
            "Debian packages are missing, as follows. Suggest:\n\n"
            "sudo apt install {}".format(" ".join(missing_packages))
        )
        log.critical(msg)
        raise ValueError(msg)


# =============================================================================
# Get the environment from a subprocess in Windows
# =============================================================================

def validate_pair(ob: Any) -> bool:
    """
    Does the object have length 2?
    """
    try:
        if len(ob) != 2:
            log.warning("Unexpected result: {!r}".format(ob))
            raise ValueError()
    except ValueError:
        return False
    return True


def consume(iterator: Iterator[Any]) -> None:
    """
    Consume all remaining values of an iterator.

    A reminder: iterable versus iterator:
    https://anandology.com/python-practice-book/iterators.html.
    """
    try:
        while True:
            next(iterator)
    except StopIteration:
        pass


def windows_get_environment_from_batch_command(
        env_cmd: Union[str, List[str]],
        initial_env: Dict[str, str] = None) -> Dict[str, str]:
    """
    Take a command (either a single command or list of arguments) and return
    the environment created after running that command. Note that the command
    must be a batch (``.bat``) file or ``.cmd`` file, or the changes to the
    environment will not be captured.

    If ``initial_env`` is supplied, it is used as the initial environment
    passed to the child process. (Otherwise, this process's ``os.environ()``
    will be used by default.)

    From https://stackoverflow.com/questions/1214496/how-to-get-environment-from-a-subprocess-in-python,
    with decoding bug fixed for Python 3.

    PURPOSE: under Windows, ``VCVARSALL.BAT`` sets up a lot of environment
    variables to compile for a specific target architecture. We want to be able
    to read them, not to replicate its work.
    
    METHOD: create a composite command that executes the specified command, 
    then echoes an unusual string tag, then prints the environment via ``SET``;
    capture the output, work out what came from ``SET``.

    Args:
        env_cmd: command, or list of command arguments
        initial_env: optional dictionary containing initial environment

    Returns:
        dict: environment created after running the command
    """  # noqa
    if not isinstance(env_cmd, (list, tuple)):
        env_cmd = [env_cmd]
    # construct the command that will alter the environment
    env_cmd = subprocess.list2cmdline(env_cmd)
    # create a tag so we can tell in the output when the proc is done
    tag = '+/!+/!+/! Finished command to set/print env +/!+/!+/!'  # RNC
    # construct a cmd.exe command to do accomplish this
    cmd = 'cmd.exe /s /c "{env_cmd} && echo "{tag}" && set"'.format(
        env_cmd=env_cmd, tag=tag)
    # launch the process
    log.info("Fetching environment using command: {}".format(env_cmd))
    log.debug("Full command: {}".format(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=initial_env)
    # parse the output sent to stdout
    encoding = sys.getdefaultencoding()

    def gen_lines() -> Generator[str, None, None]:  # RNC: fix decode problem
        for line in proc.stdout:
            yield line.decode(encoding)

    # define a way to handle each KEY=VALUE line
    def handle_line(line: str) -> Tuple[str, str]:  # RNC: as function
        # noinspection PyTypeChecker
        parts = line.rstrip().split('=', 1)
        # split("=", 1) means "split at '=' and do at most 1 split"
        if len(parts) < 2:
            return parts[0], ""
        return parts[0], parts[1]

    lines = gen_lines()  # RNC
    # consume whatever output occurs until the tag is reached
    consume(itertools.takewhile(lambda l: tag not in l, lines))
    # ... RNC: note that itertools.takewhile() generates values not matching
    #     the condition, but then consumes the condition value itself. So the
    #     tag's already gone. Example:
    #
    #   def gen():
    #       mylist = [1, 2, 3, 4, 5]
    #       for x in mylist:
    #           yield x
    #
    #   g = gen()
    #   list(itertools.takewhile(lambda x: x != 3, g))  # [1, 2]
    #   next(g)  # 4, not 3
    #
    # parse key/values into pairs
    pairs = map(handle_line, lines)
    # make sure the pairs are valid (this also eliminates the tag)
    valid_pairs = filter(validate_pair, pairs)
    # construct a dictionary of the pairs
    result = dict(valid_pairs)  # consumes generator
    # let the process finish
    proc.communicate()
    log.debug("Fetched environment:\n" + pformat(result))
    return result


# =============================================================================
# Check for a special environment danger (vulnerability) in Windows
# =============================================================================

def contains_unquoted_target(x: str,
                             quote: str = '"', target: str = '&') -> bool:
    """
    Checks if ``target`` exists in ``x`` outside quotes (as defined by
    ``quote``). Principal use: from
    :func:`contains_unquoted_ampersand_dangerous_to_windows`.
    """
    in_quote = False
    for c in x:
        if c == quote:
            in_quote = not in_quote
        elif c == target:
            if not in_quote:
                return True
    return False


def contains_unquoted_ampersand_dangerous_to_windows(x: str) -> bool:
    """
    Under Windows, if an ampersand is in a path and is not quoted, it'll break
    lots of things.
    See https://stackoverflow.com/questions/34124636.
    Simple example:

    .. code-block:: bat

        set RUBBISH=a & b           # 'b' is not recognizable as a... command
        set RUBBISH='a & b'         # 'b'' is not recognizable as a... command
        set RUBBISH="a & b"         # OK

    ... and you get similar knock-on effects, e.g. if you set RUBBISH using the
    Control Panel to the literal

    .. code-block:: bat

        a & dir

    and then do

    .. code-block:: bat

        echo %RUBBISH%

    it will (1) print "a" and then (2) print a directory listing as it RUNS
    "dir"! That's pretty dreadful.

    See also
        https://www.thesecurityfactory.be/command-injection-windows.html

    Anyway, this is a sanity check for that sort of thing.
    """
    return contains_unquoted_target(x, quote='"', target='&')
