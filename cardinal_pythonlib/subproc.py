#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/subproc.py

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
"""

import atexit
import logging
from multiprocessing.dummy import Pool  # thread pool
from queue import Queue
from subprocess import (
    check_call,
    PIPE,
    Popen,
    TimeoutExpired,
)
import sys
from threading import Thread
from time import sleep
from typing import Any, BinaryIO, List, Tuple, Union

from cardinal_pythonlib.logs import BraceStyleAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# Constants and constant-like singletons
# =============================================================================

class SubprocSource(object):
    pass


SOURCE_STDOUT = SubprocSource()
SOURCE_STDERR = SubprocSource()


class SubprocCommand(object):
    pass


TERMINATE_SUBPROCESS = SubprocCommand()


# =============================================================================
# Processes that we're running
# =============================================================================

processes = []  # type: List[Popen]
proc_args_list = []  # type: List[List[str]]
# ... to report back which process failed, if any did


# =============================================================================
# Exiting
# =============================================================================

@atexit.register
def kill_child_processes() -> None:
    """
    Kills children of this process that were registered in the
    :data:`processes` variable.

    Use with ``@atexit.register``.
    """
    timeout_sec = 5
    for p in processes:
        try:
            p.wait(timeout_sec)
        except TimeoutExpired:
            # failed to close
            p.kill()  # you're dead


def fail() -> None:
    """
    Call when a child process has failed, and this will print an error
    message to ``stdout`` and execute ``sys.exit(1)`` (which will, in turn,
    call any ``atexit`` handler to kill children of this process).
    """
    print("\nPROCESS FAILED; EXITING ALL\n")
    sys.exit(1)  # will call the atexit handler and kill everything else


# =============================================================================
# Subprocess handling
# =============================================================================

def check_call_process(args: List[str]) -> None:
    """
    Logs the command arguments, then executes the command via
    :func:`subprocess.check_call`.
    """
    log.debug("{!r}", args)
    check_call(args)


def start_process(args: List[str],
                  stdin: Any = None,
                  stdout: Any = None,
                  stderr: Any = None) -> Popen:
    """
    Launch a child process and record it in our :data:`processes` variable.

    Args:
        args: program and its arguments, as a list
        stdin: typically None
        stdout: use None to perform no routing, which preserves console colour!
            Otherwise, specify somewhere to route stdout. See subprocess
            documentation. If either is PIPE, you'll need to deal with the
            output.
        stderr: As above. You can use stderr=STDOUT to route stderr to the same
            place as stdout.

    Returns:
        The process object (which is also stored in :data:`processes`).
    """
    log.debug("{!r}", args)
    global processes
    global proc_args_list
    proc = Popen(args, stdin=stdin, stdout=stdout, stderr=stderr)
    # proc = Popen(args, stdin=None, stdout=PIPE, stderr=STDOUT)
    # proc = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
    # Can't preserve colour: http://stackoverflow.com/questions/13299550/preserve-colored-output-from-python-os-popen  # noqa
    processes.append(proc)
    proc_args_list.append(args)
    return proc


def wait_for_processes(die_on_failure: bool = True,
                       timeout_sec: float = 1) -> None:
    """
    Wait for child processes (catalogued in :data:`processes`) to finish.

    If ``die_on_failure`` is ``True``, then whenever a subprocess returns
    failure, all are killed.

    If ``timeout_sec`` is None, the function waits for its first process to
    complete, then waits for the second, etc. So a subprocess dying does not
    trigger a full quit instantly (or potentially for ages).

    If ``timeout_sec`` is something else, each process is tried for that time;
    if it quits within that time, well and good (successful quit -> continue
    waiting for the others; failure -> kill everything, if ``die_on_failure``);
    if it doesn't, we try the next. That is much more responsive.

    """
    global processes
    global proc_args_list
    n = len(processes)
    Pool(n).map(print_lines, processes)  # in case of PIPE
    something_running = True
    while something_running:
        something_running = False
        for i, p in enumerate(processes):
            try:
                retcode = p.wait(timeout=timeout_sec)
                if retcode == 0:
                    log.info("Process #{} (of {}) exited cleanly", i, n)
                if retcode != 0:
                    log.critical(
                        "Process #{} (of {}) exited with return code {} "
                        "(indicating failure); its args were: {!r}",
                        i, n, retcode, proc_args_list[i])
                    if die_on_failure:
                        log.critical("Exiting top-level process (will kill "
                                     "all other children)")
                        fail()  # exit this process, therefore kill its children  # noqa
            except TimeoutExpired:
                something_running = True
    processes.clear()
    proc_args_list.clear()


def print_lines(process: Popen) -> None:
    """
    Let a subprocess :func:`communicate`, then write both its ``stdout`` and
    its ``stderr`` to our ``stdout``.
    """
    out, err = process.communicate()
    if out:
        for line in out.decode("utf-8").splitlines():
            print(line)
    if err:
        for line in err.decode("utf-8").splitlines():
            print(line)


def run_multiple_processes(args_list: List[List[str]],
                           die_on_failure: bool = True) -> None:
    """
    Fire up multiple processes, and wait for them to finihs.

    Args:
        args_list: command arguments for each process
        die_on_failure: see :func:`wait_for_processes`
    """
    for procargs in args_list:
        start_process(procargs)
    # Wait for them all to finish
    wait_for_processes(die_on_failure=die_on_failure)


class AsynchronousFileReader(Thread):
    """
    Helper class to implement asynchronous reading of a file
    in a separate thread. Pushes read lines on a queue to
    be consumed in another thread.

    Modified from
    http://stefaanlippens.net/python-asynchronous-subprocess-pipe-reading/.
    """

    def __init__(self,
                 fd: BinaryIO,
                 queue: Queue,
                 encoding: str,
                 line_terminators: List[str] = None,
                 cmdargs: List[str] = None,
                 suppress_decoding_errors: bool = True) -> None:
        """
        Args:
            fd: file-like object to read from
            queue: queue to write to
            encoding: encoding to use when reading from the file
            line_terminators: valid line terminators
            cmdargs: for display purposes only: command that produced/is
                producing the file-like object
            suppress_decoding_errors: trap any ``UnicodeDecodeError``?
        """
        assert isinstance(queue, Queue)
        assert callable(fd.readline)
        super().__init__()
        self._fd = fd
        self._queue = queue
        self._encoding = encoding
        self._line_terminators = line_terminators or ["\n"]  # type: List[str]
        self._cmdargs = cmdargs or []  # type: List[str]
        self._suppress_decoding_errors = suppress_decoding_errors

    def run(self) -> None:
        """
        Read lines and put them on the queue.
        """
        fd = self._fd
        encoding = self._encoding
        line_terminators = self._line_terminators
        queue = self._queue
        buf = ""
        while True:
            try:
                c = fd.read(1).decode(encoding)
            except UnicodeDecodeError as e:
                log.warning("Decoding error from {!r}: {!r}", self._cmdargs, e)
                if self._suppress_decoding_errors:
                    continue
                else:
                    raise
            # log.critical("c={!r}, returncode={!r}", c, p.returncode)
            if not c:
                # Subprocess has finished
                return
            buf += c
            # log.critical("buf={!r}", buf)
            # noinspection PyTypeChecker
            for t in line_terminators:
                try:
                    t_idx = buf.index(t) + len(t)  # include terminator
                    fragment = buf[:t_idx]
                    buf = buf[t_idx:]
                    queue.put(fragment)
                except ValueError:
                    pass

    def eof(self) -> bool:
        """
        Check whether there is no more content to expect.
        """
        return not self.is_alive() and self._queue.empty()


def mimic_user_input(
        args: List[str],
        source_challenge_response: List[Tuple[SubprocSource,
                                              str,
                                              Union[str, SubprocCommand]]],
        line_terminators: List[str] = None,
        print_stdout: bool = False,
        print_stderr: bool = False,
        print_stdin: bool = False,
        stdin_encoding: str = None,
        stdout_encoding: str = None,
        suppress_decoding_errors: bool = True,
        sleep_time_s: float = 0.1) -> None:
    r"""
    Run an external command. Pretend to be a human by sending text to the
    subcommand (responses) when the external command sends us triggers
    (challenges).
    
    This is a bit nasty.
    
    Args:
        args: command-line arguments
        source_challenge_response: list of tuples of the format ``(challsrc,
            challenge, response)``; see below
        line_terminators: valid line terminators
        print_stdout: 
        print_stderr: 
        print_stdin: 
        stdin_encoding: 
        stdout_encoding: 
        suppress_decoding_errors: trap any ``UnicodeDecodeError``?
        sleep_time_s:
        
    The ``(challsrc, challenge, response)`` tuples have this meaning:
    
    - ``challsrc``: where is the challenge coming from? Must be one of the
      objects :data:`SOURCE_STDOUT` or :data:`SOURCE_STDERR`;
    - ``challenge``: text of challenge
    - ``response``: text of response (send to the subcommand's ``stdin``).
    
    Example (modified from :class:`CorruptedZipReader`):

    .. code-block:: python
    
        from cardinal_pythonlib.subproc import *
        
        SOURCE_FILENAME = "corrupt.zip"
        TMP_DIR = "/tmp"
        OUTPUT_FILENAME = "rescued.zip"
    
        cmdargs = [
            "zip",  # Linux zip tool
            "-FF",  # or "--fixfix": "fix very broken things"
            SOURCE_FILENAME,  # input file
            "--temp-path", TMP_DIR,  # temporary storage path
            "--out", OUTPUT_FILENAME  # output file
        ]

        # We would like to be able to say "y" automatically to
        # "Is this a single-disk archive?  (y/n):"
        # The source code (api.c, zip.c, zipfile.c), from
        # ftp://ftp.info-zip.org/pub/infozip/src/ , suggests that "-q"
        # should do this (internally "-q" sets "noisy = 0") - but in
        # practice it doesn't work. This is a critical switch.
        # Therefore we will do something very ugly, and send raw text via
        # stdin.

        ZIP_PROMPTS_RESPONSES = [
            (SOURCE_STDOUT, "Is this a single-disk archive?  (y/n): ", "y\n"),
            (SOURCE_STDOUT, " or ENTER  (try reading this split again): ", "q\n"),
            (SOURCE_STDERR,
             "zip: malloc.c:2394: sysmalloc: Assertion `(old_top == initial_top (av) "
             "&& old_size == 0) || ((unsigned long) (old_size) >= MINSIZE && "
             "prev_inuse (old_top) && ((unsigned long) old_end & (pagesize - 1)) "
             "== 0)' failed.", TERMINATE_SUBPROCESS),
        ]
        ZIP_STDOUT_TERMINATORS = ["\n", "): "]

        mimic_user_input(cmdargs,
                         source_challenge_response=ZIP_PROMPTS_RESPONSES,
                         line_terminators=ZIP_STDOUT_TERMINATORS,
                         print_stdout=show_zip_output,
                         print_stdin=show_zip_output)

    """  # noqa
    line_terminators = line_terminators or ["\n"]  # type: List[str]
    stdin_encoding = stdin_encoding or sys.getdefaultencoding()
    stdout_encoding = stdout_encoding or sys.getdefaultencoding()

    # Launch the command
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, bufsize=0)

    # Launch the asynchronous readers of stdout and stderr
    stdout_queue = Queue()
    # noinspection PyTypeChecker
    stdout_reader = AsynchronousFileReader(
        fd=p.stdout,
        queue=stdout_queue,
        encoding=stdout_encoding,
        line_terminators=line_terminators,
        cmdargs=args,
        suppress_decoding_errors=suppress_decoding_errors
    )
    stdout_reader.start()
    stderr_queue = Queue()
    # noinspection PyTypeChecker
    stderr_reader = AsynchronousFileReader(
        fd=p.stderr,
        queue=stderr_queue,
        encoding=stdout_encoding,  # same as stdout
        line_terminators=line_terminators,
        cmdargs=args,
        suppress_decoding_errors=suppress_decoding_errors
    )
    stderr_reader.start()

    while not stdout_reader.eof() or not stderr_reader.eof():
        lines_with_source = []  # type: List[Tuple[SubprocSource, str]]
        while not stdout_queue.empty():
            lines_with_source.append((SOURCE_STDOUT, stdout_queue.get()))
        while not stderr_queue.empty():
            lines_with_source.append((SOURCE_STDERR, stderr_queue.get()))

        for src, line in lines_with_source:
            if src is SOURCE_STDOUT and print_stdout:
                print(line, end="")  # terminator already in line
            if src is SOURCE_STDERR and print_stderr:
                print(line, end="")  # terminator already in line
            for challsrc, challenge, response in source_challenge_response:
                # log.critical("challsrc={!r}", challsrc)
                # log.critical("challenge={!r}", challenge)
                # log.critical("line={!r}", line)
                # log.critical("response={!r}", response)
                if challsrc != src:
                    continue
                if challenge in line:
                    if response is TERMINATE_SUBPROCESS:
                        log.warning("Terminating subprocess {!r} because input "
                                    "{!r} received", args, challenge)
                        p.kill()
                        return
                    else:
                        p.stdin.write(response.encode(stdin_encoding))
                        p.stdin.flush()
                        if print_stdin:
                            print(response, end="")

        # Sleep a bit before asking the readers again.
        sleep(sleep_time_s)

    stdout_reader.join()
    stderr_reader.join()
    p.stdout.close()
    p.stderr.close()
