#!/usr/bin/env python
# cardinal_pythonlib/ui.py

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

**Support functions for user interaction.**

"""


import getpass
import os
from typing import Optional

try:
    import tkinter
    from tkinter import filedialog
except ImportError:
    tkinter = None  # make type checker happy
    filedialog = None  # make type checker happy
    if not os.environ["_SPHINX_AUTODOC_IN_PROGRESS"]:
        raise


def ask_user(prompt: str, default: str = None) -> Optional[str]:
    """
    Prompts the user, with a default. Returns user input from ``stdin``.
    """
    if default is None:
        prompt += ": "
    else:
        prompt += " [" + default + "]: "
    result = input(prompt)
    return result if len(result) > 0 else default


def ask_user_password(prompt: str) -> str:
    """
    Read a password from the console.
    """
    return getpass.getpass(prompt + ": ")


def get_save_as_filename(defaultfilename: str,
                         defaultextension: str,
                         title: str = "Save As") -> str:
    """
    Provides a GUI "Save As" dialogue (via ``tkinter``) and returns the
    filename.
    """
    root = tkinter.Tk()  # create and get Tk topmost window
    # (don't do this too early; the command prompt loses focus)
    root.withdraw()  # won't need this; this gets rid of a blank Tk window
    root.attributes('-topmost', True)  # makes the tk window topmost
    filename = filedialog.asksaveasfilename(
        initialfile=defaultfilename,
        defaultextension=defaultextension,
        parent=root,
        title=title
    )
    root.attributes('-topmost', False)  # stop the tk window being topmost
    return filename


def get_open_filename(defaultfilename: str,
                      defaultextension: str,
                      title: str = "Open") -> str:
    """
    Provides a GUI "Open" dialogue (via ``tkinter``) and returns the filename.
    """
    root = tkinter.Tk()  # create and get Tk topmost window
    # (don't do this too early; the command prompt loses focus)
    root.withdraw()  # won't need this; this gets rid of a blank Tk window
    root.attributes('-topmost', True)  # makes the tk window topmost
    filename = filedialog.askopenfilename(
        initialfile=defaultfilename,
        defaultextension=defaultextension,
        parent=root,
        title=title
    )
    root.attributes('-topmost', False)  # stop the tk window being topmost
    return filename
