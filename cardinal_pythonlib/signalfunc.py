#!/usr/bin/env python
# cardinal_pythonlib/signalfunc.py

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

**Support functions to handle OS signals that may cause trouble.**

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
    """
    Logs that ``CTRL-C`` has been pressed but does nothing else.
    """
    log.critical("Ignoring CTRL+C (signal {}); use the GUI to quit".format(
        signum))


# noinspection PyUnusedLocal
def ctrl_break_trapper(signum: int, stackframe) -> None:
    """
    Logs that ``CTRL-BREAK`` has been pressed but does nothing else.
    """
    log.critical("Ignoring CTRL+BREAK (signal {}); use the GUI to quit".format(
        signum))


# noinspection PyUnusedLocal
def sigterm_trapper(signum: int, stackframe) -> None:
    """
    Logs that ``SIGTERM`` has been received but does nothing else.
    """
    log.critical("Ignoring SIGTERM (signal {}); use the GUI to quit".format(
        signum))


def trap_ctrl_c_ctrl_break() -> None:
    """
    Prevent ``CTRL-C``, ``CTRL-BREAK``, and similar signals from doing
    anything.
    
    See
    
    - https://docs.python.org/3/library/signal.html#signal.SIG_IGN
    - https://msdn.microsoft.com/en-us/library/xdkz3x12.aspx
    - https://msdn.microsoft.com/en-us/library/windows/desktop/ms682541(v=vs.85).aspx

    Under Windows, the only options are:
    
      =========== ======================= =====================================
      Signal      Meaning                 Comment
      =========== ======================= =====================================
      SIGABRT     abnormal termination
      SIGFPE      floating-point error
      SIGILL      illegal instruction
      SIGINT      CTRL+C signal           -- trapped here
      SIGSEGV     illegal storage access
      SIGTERM     termination request     -- trapped here
      SIGBREAK    CTRL+BREAK              -- trapped here under Windows
      =========== ======================= =====================================

    In Linux, you also find:

      =========== =============================
      Signal      Meaning
      =========== =============================
      SIGBUS      bus error / unaligned access
      =========== =============================

    To ignore, can do:
    
    .. code-block:: python
    
      signal.signal(signal.SIGINT, signal.SIG_IGN)  # SIG_IGN = "ignore me"
      
    or pass a specified handler, as in the code here.
    """  # noqa

    signal.signal(signal.SIGINT, ctrl_c_trapper)
    signal.signal(signal.SIGTERM, sigterm_trapper)
    if platform.system() == 'Windows':
        # SIGBREAK isn't in the Linux signal module
        # noinspection PyUnresolvedReferences
        signal.signal(signal.SIGBREAK, ctrl_break_trapper)
