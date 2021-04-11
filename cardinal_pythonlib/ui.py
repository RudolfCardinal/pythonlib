#!/usr/bin/env python
# cardinal_pythonlib/ui.py

"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

**Support functions for user interaction.**

"""

import os

# For back compatibility (these functions used to be in this file):
# noinspection PyUnresolvedReferences
from cardinal_pythonlib.ui_commandline import ask_user, ask_user_password

try:
    import tkinter
    from tkinter import filedialog
except ImportError:
    tkinter = None  # make type checker happy
    filedialog = None  # make type checker happy
    if not os.environ.get("_SPHINX_AUTODOC_IN_PROGRESS", None):
        raise


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
