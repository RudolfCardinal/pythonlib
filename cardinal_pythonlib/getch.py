#!/usr/bin/env python
# cardinal_pythonlib/getch.py

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

**Offers the getch() and kbhit() functions, and other terminal-related stuff.**

In this module, :func:`getch` and :func:`kbhit` are mapped to their OS-specific
versions.

"""

import atexit
import select
import sys

try:
    import msvcrt  # Windows only
    termios = None
    tty = None
except ImportError:
    msvcrt = None
    import termios  # Unix only
    import tty  # requires termios, so Unix only


# =============================================================================
# Read single character, waiting for it
# =============================================================================
# http://stackoverflow.com/questions/510357/python-read-a-single-character-from-the-user  # noqa
# http://home.wlu.edu/~levys/software/kbhit.py
# ... modified a little

def _getch_windows() -> str:
    """
    Under Windows, wets a single character from standard input. Does not echo
    to the screen.
    """
    return msvcrt.getch().decode('utf-8')


def _getch_unix() -> str:
    """
    Under UNIX, gets a single character from standard input. Does not echo to
    the screen. Note that the terminal will have been pre-configured, below.
    """
    return sys.stdin.read(1)


# =============================================================================
# Is a keystroke available?
# =============================================================================
# http://code.activestate.com/recipes/572182-how-to-implement-kbhit-on-linux/
# http://stackoverflow.com/questions/2408560/python-nonblocking-console-input

def _kbhit_windows() -> bool:
    """
    Under Windows: is a keystroke available?
    """
    return msvcrt.kbhit()


def _kbhit_unix() -> bool:
    """
    Under UNIX: is a keystroke available?
    """
    dr, dw, de = select.select([sys.stdin], [], [], 0)
    return dr != []


# =============================================================================
# Configure terminal (UNIX)
# =============================================================================

def set_normal_term() -> None:
    """
    Under UNIX: switch to a normal terminal. (Compare :func:`set_curses_term`.)
    """
    termios.tcsetattr(_fd, termios.TCSAFLUSH, _old_term)


def set_curses_term() -> None:
    """
    Under UNIX: switch to an unbuffered, curses-style terminal. (Compare
    :func:`set_normal_term`.)
    """
    termios.tcsetattr(_fd, termios.TCSAFLUSH, _new_term)


# =============================================================================
# Set up for specific OS
# =============================================================================

if msvcrt:
    # -------------------------------------------------------------------------
    # Windows
    # -------------------------------------------------------------------------
    getch = _getch_windows
    kbhit = _kbhit_windows
else:
    # -------------------------------------------------------------------------
    # Unix
    # -------------------------------------------------------------------------
    getch = _getch_unix
    kbhit = _kbhit_unix

    # save the terminal settings
    _fd = sys.stdin.fileno()
    _new_term = termios.tcgetattr(_fd)
    _old_term = termios.tcgetattr(_fd)
    # new terminal setting unbuffered
    _new_term[3] = (_new_term[3] & ~termios.ICANON & ~termios.ECHO)
    _new_term[6][termios.VMIN] = 1
    _new_term[6][termios.VTIME] = 0

    atexit.register(set_normal_term)
    set_curses_term()
