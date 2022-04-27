#!/usr/bin/env python
# cardinal_pythonlib/process.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Support functions for process/external command management.**

"""

import shlex
import subprocess
import sys
import traceback
from typing import BinaryIO, List, Sequence, Set, Tuple

import psutil

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Get otput of extermnal commands
# =============================================================================


def get_external_command_output(command: str) -> bytes:
    """
    Takes a command-line command, executes it, and returns its ``stdout``
    output.

    Args:
        command: command string

    Returns:
        output from the command as ``bytes``

    """
    args = shlex.split(command)
    ret = subprocess.check_output(args)  # this needs Python 2.7 or higher
    return ret


def get_pipe_series_output(
    commands: Sequence[str], stdinput: BinaryIO = None
) -> bytes:
    """
    Get the output from a piped series of commands.

    Args:
        commands: sequence of command strings
        stdinput: optional ``stdin`` data to feed into the start of the pipe

    Returns:
        ``stdout`` from the end of the pipe

    """
    # Python arrays indexes are zero-based, i.e. an array is indexed from
    # 0 to len(array)-1.
    # The range/xrange commands, by default, start at 0 and go to one less
    # than the maximum specified.

    # print commands
    processes = []  # type: List[subprocess.Popen]
    for i in range(len(commands)):
        if i == 0:  # first processes
            processes.append(
                subprocess.Popen(
                    shlex.split(commands[i]),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                )
            )
        else:  # subsequent ones
            processes.append(
                subprocess.Popen(
                    shlex.split(commands[i]),
                    stdin=processes[i - 1].stdout,
                    stdout=subprocess.PIPE,
                )
            )
    return processes[len(processes) - 1].communicate(stdinput)[0]
    # communicate() returns a tuple; 0=stdout, 1=stderr; so this returns stdout


# Also, simple commands: use os.system(command)


# =============================================================================
# Launch external file using OS's launcher
# =============================================================================


def launch_external_file(filename: str, raise_if_fails: bool = False) -> None:
    """
    Launches a file using the operating system's standard launcher.

    Args:
        filename: file to launch
        raise_if_fails: raise any exceptions from
            ``subprocess.call(["xdg-open", filename])`` (Linux)
            or ``os.startfile(filename)`` (otherwise)? If not, exceptions
            are suppressed.

    """
    log.info("Launching external file: {!r}", filename)
    try:
        if sys.platform.startswith("linux"):
            cmdargs = ["xdg-open", filename]
            # log.debug("... command: {!r}", cmdargs)
            subprocess.call(cmdargs)
        else:
            # log.debug("... with os.startfile()")
            # noinspection PyUnresolvedReferences
            os.startfile(filename)
    except Exception as e:
        log.critical(
            "Error launching {!r}: error was {}.\n\n{}",
            filename,
            str(e),
            traceback.format_exc(),
        )
        if raise_if_fails:
            raise


# =============================================================================
# Kill a process tree. Particularly useful for Windows, where a plain "kill()"
# (via subprocess) can leave orphans.
# =============================================================================


def kill_proc_tree(
    pid: int, including_parent: bool = True, timeout_s: float = 5
) -> Tuple[Set[psutil.Process], Set[psutil.Process]]:
    """
    Kills a tree of processes, starting with the parent. Slightly modified from
    https://stackoverflow.com/questions/1230669/subprocess-deleting-child-processes-in-windows.

    Args:
        pid: process ID of the parent
        including_parent: kill the parent too?
        timeout_s: timeout to wait for processes to close

    Returns:
        tuple: ``(gone, still_alive)``, where both are sets of
        :class:`psutil.Process` objects

    """  # noqa
    parent = psutil.Process(pid)
    to_kill = parent.children(recursive=True)  # type: List[psutil.Process]
    if including_parent:
        to_kill.append(parent)
    for proc in to_kill:
        proc.kill()  # SIGKILL
    gone, still_alive = psutil.wait_procs(to_kill, timeout=timeout_s)
    return gone, still_alive


# =============================================================================
# nice_call
# =============================================================================


def nice_call(
    *popenargs, timeout: float = None, cleanup_timeout: float = None, **kwargs
) -> int:
    """
    Like :func:`subprocess.call`, but give the child process time to
    clean up and communicate if a :exc:`KeyboardInterrupt` is raised.

    Modified from
    https://stackoverflow.com/questions/34458583/python-subprocess-call-doesnt-handle-signal-correctly
    """  # noqa
    with subprocess.Popen(*popenargs, **kwargs) as p:
        try:
            return p.wait(timeout=timeout)
        except KeyboardInterrupt:
            log.error("KeyboardInterrupt received")
            if cleanup_timeout:
                # Wait again, now that the child has received SIGINT, too.
                log.info(
                    f"Waiting {cleanup_timeout} seconds "
                    f"for child process {p.pid} to finish..."
                )
                try:
                    p.wait(timeout=cleanup_timeout)  # may raise TimeoutExpired
                    log.info(f"Child process {p.pid} shut down cleanly")
                except subprocess.TimeoutExpired:
                    log.info(f"Killing child process {p.pid}")
                    p.kill()
                    p.wait()
            raise  # propagate KeyboardInterrupt up through Python program
        except Exception:
            log.error(f"Error with child process {p.pid}. Killing it...")
            p.kill()
            p.wait()
            log.info(f"Child process {p.pid} killed")
            raise
