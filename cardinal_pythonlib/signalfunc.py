#!/usr/bin/env python
# cardinal_pythonlib/signalfunc.py

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

Support functions to do with the core language.

"""

import logging
import platform
import signal

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Signal handlers
# =============================================================================

# noinspection PyUnusedLocal
def ctrl_c_trapper(signum: int, stackframe) -> None:
    log.critical("Ignoring CTRL+C (signal {}); use the GUI to quit".format(
        signum))


# noinspection PyUnusedLocal
def ctrl_break_trapper(signum: int, stackframe) -> None:
    log.critical("Ignoring CTRL+BREAK (signal {}); use the GUI to quit".format(
        signum))


# noinspection PyUnusedLocal
def sigterm_trapper(signum: int, stackframe) -> None:
    log.critical("Ignoring SIGTERM (signal {}); use the GUI to quit".format(
        signum))


def trap_ctrl_c_ctrl_break() -> None:
    # - https://stackoverflow.com/questions/1112343/how-do-i-capture-sigint-in-python  # noqa
    # - https://docs.python.org/3/library/signal.html#signal.SIG_IGN
    # - https://msdn.microsoft.com/en-us/library/xdkz3x12.aspx
    # - https://msdn.microsoft.com/en-us/library/windows/desktop/ms682541(v=vs.85).aspx  # noqa
    #
    # Under Windows, only options are:
    #   SIGABRT     abnormal termination
    #   SIGFPE      floating-point error
    #   SIGILL      illegal instruction
    #   SIGINT      CTRL+C signal           -- trapped here
    #   SIGSEGV     illegal storage access
    #   SIGTERM     termination request     -- trapped here
    #   SIGBREAK    CTRL+BREAK              -- trapped here under Windows
    #
    # In Linux, you also find:
    #   SIGBUS      bus error / unaligned access
    #
    # To ignore, can do:
    #   signal.signal(signal.SIGINT, signal.SIG_IGN)  # SIG_IGN = "ignore me"
    # or pass a specified handler, as below.

    signal.signal(signal.SIGINT, ctrl_c_trapper)
    signal.signal(signal.SIGTERM, sigterm_trapper)
    if platform.system() == 'Windows':
        # SIGBREAK isn't in the Linux signal module
        # noinspection PyUnresolvedReferences
        signal.signal(signal.SIGBREAK, ctrl_break_trapper)
