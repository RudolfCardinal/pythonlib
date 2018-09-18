#!/usr/bin/env python
# cardinal_pythonlib/tee.py

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

**Support functions for "tee" functionality.**

DEVELOPMENT NOTES

Initial failure:

- We can copy the Python logging output to a file; that's part of the 
  standard logging facility.
- We can also redirect our own stdout/stderr to a file and/or print a copy;
  that's pretty easy to.
- We can manually capture subprocess stdout/stderr.
- We can redirect our own and subprocess stdout/stderr to a genuine file by
  duplicating the file descriptor(s):
  https://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/
- However, that file descriptor duplication method needs our file-like object
  to behave properly like a C-level file. That precludes the simpler kinds of
  "tee" behaviour in which a Python class pretends to be a file by 
  implementing write(), close(), flush() methods.

So:

- redirect plain Python stderr/stdout
- handle subprocess stuff 

See

- https://stackoverflow.com/questions/616645/how-do-i-duplicate-sys-stdout-to-a-log-file-in-python
- https://stackoverflow.com/questions/24931/how-to-capture-python-interpreters-and-or-cmd-exes-output-from-a-python-script
- https://www.python.org/dev/peps/pep-0343/

- https://stackoverflow.com/questions/4675728/redirect-stdout-to-a-file-in-python
- https://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/ 

- https://stackoverflow.com/questions/2996887/how-to-replicate-tee-behavior-in-python-when-using-subprocess

- https://stackoverflow.com/questions/4984428/python-subprocess-get-childrens-output-to-file-and-terminal/4985080#4985080

"""  # noqa

from contextlib import contextmanager
from io import TextIOWrapper
import logging
import os
from subprocess import PIPE, Popen
import sys
from threading import Thread
import traceback
from typing import IO, List, TextIO

from cardinal_pythonlib.logs import (
    BraceStyleAdapter,
    get_monochrome_handler,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


def tee(infile: IO, *files: IO) -> Thread:
    r"""
    Print the file-like object ``infile`` to the file-like object(s) ``files``
    in a separate thread.
    
    Starts and returns that thread.
    
    The type (text, binary) must MATCH across all files.

    From 
    https://stackoverflow.com/questions/4984428/python-subprocess-get-childrens-output-to-file-and-terminal

    A note on text versus binary IO:

    TEXT files include:
    
    - files opened in text mode (``"r"``, ``"rt"``, ``"w"``, ``"wt"``)
    - ``sys.stdin``, ``sys.stdout``
    - ``io.StringIO()``; see
      https://docs.python.org/3/glossary.html#term-text-file

    BINARY files include:
    
    - files opened in binary mode (``"rb"``, ``"wb"``, ``"rb+"``...)
    - ``sys.stdin.buffer``, ``sys.stdout.buffer``
    - ``io.BytesIO()``
    - ``gzip.GzipFile()``; see
      https://docs.python.org/3/glossary.html#term-binary-file

    .. code-block:: bash
 
        $ python3  # don't get confused and use Python 2 by mistake!
        
    .. code-block:: python
 
        t = open("/tmp/text.txt", "r+t")  # text mode is default
        b = open("/tmp/bin.bin", "r+b")
        
        t.write("hello\n")  # OK
        # b.write("hello\n")  # raises TypeError
        
        # t.write(b"world\n")  # raises TypeError
        b.write(b"world\n")  # OK
        
        t.flush()
        b.flush()
        t.seek(0)
        b.seek(0)
        
        x = t.readline()  # "hello\n"
        y = b.readline()  # b"world\n"

    """  # noqa

    def fanout(_infile: IO, *_files: IO):
        for line in iter(_infile.readline, ''):
            for f in _files:
                f.write(line)
        infile.close()

    t = Thread(target=fanout, args=(infile,) + files)
    t.daemon = True
    t.start()
    return t


def teed_call(cmd_args,
              stdout_targets: List[TextIO] = None,
              stderr_targets: List[TextIO] = None,
              encoding: str = sys.getdefaultencoding(),
              **kwargs):
    """
    Runs a command and captures its output via :func:`tee` to one or more 
    destinations. The output is always captured (otherwise we would lose 
    control of the output and ability to ``tee`` it); if no destination is 
    specified, we add a null handler.

    We insist on ``TextIO`` output files to match ``sys.stdout`` (etc.).

    A variation on:
    https://stackoverflow.com/questions/4984428/python-subprocess-get-childrens-output-to-file-and-terminal

    Args:
        cmd_args: arguments for the command to run
        stdout_targets: file-like objects to write ``stdout`` to
        stderr_targets: file-like objects to write ``stderr`` to 
        encoding: encoding to apply to ``stdout`` and ``stderr``
        kwargs: additional arguments for :class:`subprocess.Popen`
        
    """  # noqa
    # Make a copy so we can append without damaging the original:
    stdout_targets = stdout_targets.copy() if stdout_targets else []  # type: List[TextIO]  # noqa
    stderr_targets = stderr_targets.copy() if stderr_targets else []  # type: List[TextIO]  # noqa
    p = Popen(cmd_args, stdout=PIPE, stderr=PIPE, **kwargs)
    threads = []  # type: List[Thread]
    with open(os.devnull, "w") as null:  # type: TextIO
        if not stdout_targets:
            stdout_targets.append(null)
        if not stderr_targets:
            stderr_targets.append(null)
        # Now, by default, because we're not using "universal_newlines", both
        # p.stdout and p.stderr are binary.
        stdout_txt = TextIOWrapper(p.stdout, encoding=encoding)  # type: TextIO  # noqa
        stderr_txt = TextIOWrapper(p.stderr, encoding=encoding)  # type: TextIO  # noqa
        threads.append(tee(stdout_txt, *stdout_targets))
        threads.append(tee(stderr_txt, *stderr_targets))
        for t in threads:
            t.join()  # wait for IO completion
        return p.wait()


class TeeContextManager(object):
    """
    Context manager to implement the function of the Unix ``tee`` command: that
    is, to save output to a file as well as display it to the console.

    Note that this redirects Python's ``sys.stdout`` or ``sys.stderr``, but
    doesn't redirect ``stdout``/``stderr`` from child processes -- so use
    :func:`teed_call` to run them if you want those redirected too. See
    :func:`buildfunc.run` for an example.

    Also, existing logs won't be redirected (presumably because they've already
    taken a copy of their output streams); see :func:`tee_log` for an example
    of one way to manage this.
    """

    def __init__(self,
                 file: TextIO,
                 capture_stdout: bool = False,
                 capture_stderr: bool = False) -> None:
        """
        Args:
            file: file-like object to write to. We take a file object, not a
                filename, so we can apply multiple tee filters going to the
                same file.
            capture_stdout: capture ``stdout``? Use this or ``capture_stderr``
            capture_stderr: capture ``stderr``? Use this or ``capture_stdout``

        We read the filename from ``file.name`` but this is purely cosmetic.
        """
        # Checks
        assert capture_stdout != capture_stderr, (
            "Capture either stdout or stderr, not both (use two copies if you "
            "want both redirected; if both come to the same object, we can't"
            "distinguish the source, so output gets duplicated)."
        )
        # Save variables
        self.using_stdout = capture_stdout
        self.file = file
        self.filename = file.name
        # Announce
        self.output_description = "stdout" if capture_stdout else "stderr"
        log.debug("Copying {} to file {}".format(self.output_description,
                                                 self.filename))

        # Redirect
        if self.using_stdout:
            self.underlying_stream = sys.stdout
            sys.stdout = self  # now "self" must behave as a file
        else:
            self.underlying_stream = sys.stderr
            sys.stderr = self  # now "self" must behave as a file

    def __enter__(self) -> None:
        """
        To act as a context manager.
        """
        pass

    def __exit__(self, *args) -> None:
        """
        To act as a context manager.
        """
        self.close()

    def write(self, message: str) -> None:
        """
        To act as a file.
        """
        self.underlying_stream.write(message)
        self.file.write(message)

    def flush(self) -> None:
        """
        To act as a file.
        """
        self.underlying_stream.flush()
        self.file.flush()
        os.fsync(self.file.fileno())

    def close(self) -> None:
        """
        To act as a file.
        """
        if self.underlying_stream:
            if self.using_stdout:
                sys.stdout = self.underlying_stream
            else:
                sys.stderr = self.underlying_stream
            self.underlying_stream = None
        if self.file:
            # Do NOT close the file; we don't own it.
            self.file = None
            log.debug("Finished copying {} to {}".format(
                self.output_description, self.filename))


@contextmanager
def tee_log(tee_file: TextIO, loglevel: int) -> None:
    """
    Context manager to add a file output stream to our logging system.

    Args:
        tee_file: file-like object to write to
        loglevel: log level (e.g. ``logging.DEBUG``) to use for this stream

    """
    handler = get_monochrome_handler(stream=tee_file)
    handler.setLevel(loglevel)
    rootlogger = logging.getLogger()
    rootlogger.addHandler(handler)
    # Tee the main stdout/stderr as required.
    with TeeContextManager(tee_file, capture_stdout=True):
        with TeeContextManager(tee_file, capture_stderr=True):
            try:
                yield
            except Exception:
                # We catch this so that the exception also goes to
                # the log.
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value,
                                                   exc_traceback)
                log.critical("\n" + "".join(lines))
                raise
