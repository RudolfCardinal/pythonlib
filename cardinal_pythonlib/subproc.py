#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/subproc.py

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
    timeout_sec = 5
    for p in processes:
        try:
            p.wait(timeout_sec)
        except TimeoutExpired:
            # failed to close
            p.kill()  # you're dead


def fail() -> None:
    print("\nPROCESS FAILED; EXITING ALL\n")
    sys.exit(1)  # will call the atexit handler and kill everything else


# =============================================================================
# Subprocess handling
# =============================================================================

def check_call_process(args: List[str]) -> None:
    log.debug("{!r}", args)
    check_call(args)


def start_process(args: List[str],
                  stdin: Any = None,
                  stdout: Any = None,
                  stderr: Any = None) -> Popen:
    """

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
        The process object (which is also stored in processes).
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
    If die_on_failure is True, then whenever a subprocess returns failure,
    all are killed.

    If timeout_sec is None, the function waits for its first process to
    complete, then waits for the second, etc. So a subprocess dying does not
    trigger a full quit instantly (or potentially for ages).

    If timeout_sec is something else, each process is tried for that time;
    if it quits within that time, well and good (successful quit -> continue
    waiting for the others; failure -> kill everything, if die_on_failure);
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
    out, err = process.communicate()
    if out:
        for line in out.decode("utf-8").splitlines():
            print(line)
    if err:
        for line in err.decode("utf-8").splitlines():
            print(line)


def run_multiple_processes(args_list: List[List[str]],
                           die_on_failure: bool = True) -> None:
    for procargs in args_list:
        start_process(procargs)
    # Wait for them all to finish
    wait_for_processes(die_on_failure=die_on_failure)


class AsynchronousFileReader(Thread):
    """
    Helper class to implement asynchronous reading of a file
    in a separate thread. Pushes read lines on a queue to
    be consumed in another thread.

    http://stefaanlippens.net/python-asynchronous-subprocess-pipe-reading/
    """

    def __init__(self,
                 fd: BinaryIO,
                 queue: Queue,
                 encoding: str,
                 line_terminators: List[str] = None,
                 cmdargs: List[str] = None,
                 suppress_decoding_errors: bool = True) -> None:
        assert isinstance(queue, Queue)
        assert callable(fd.readline)
        super().__init__()
        self._fd = fd
        self._queue = queue
        self._encoding = encoding
        self._line_terminators = line_terminators or ["\n"]  # type: List[str]
        self._cmdargs = cmdargs or []  # type: List[str]
        self._suppress_decoding_errors = suppress_decoding_errors

    def run(self):
        """Read lines and put them on the queue."""
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

    def eof(self):
        """Check whether there is no more content to expect."""
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
    line_terminators = line_terminators or ["\n"]  # type: List[str]
    stdin_encoding = stdin_encoding or sys.getdefaultencoding()
    stdout_encoding = stdout_encoding or sys.getdefaultencoding()

    # Launch the command
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, bufsize=0)

    # Launch the asynchronous readers of stdout and stderr
    stdout_queue = Queue()
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
