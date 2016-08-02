#!/usr/bin/env python
# -*- encoding: utf8 -*-

"""Support functions for user interaction.

Author: Rudolf Cardinal (rudolf@pobox.com)
Created: 2009
Last update: 24 Sep 2015

Copyright/licensing:

    Copyright (C) 2009-2015 Rudolf Cardinal (rudolf@pobox.com).

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""


import errno
import getpass
import os
# noinspection PyUnresolvedReferences
# from six.moves import input
import sys
from typing import Optional
if sys.version_info > (3,):
    # Python 3
    import tkinter
    import tkinter.filedialog
    filedialog = tkinter.filedialog
else:
    # Python 2
    # noinspection PyUnresolvedReferences
    import Tkinter
    tkinter = Tkinter
    # noinspection PyUnresolvedReferences
    import tkFileDialog
    filedialog = tkFileDialog


def ask_user(prompt: str,
             default: str = None,
             to_unicode: bool = False) -> Optional[str]:
    """Prompts the user, with a default. Returns str or unicode."""
    if default is None:
        prompt += ": "
    else:
        prompt += " [" + default + "]: "
    result = input(prompt.encode(sys.stdout.encoding))
    if to_unicode:
        result = result.decode(sys.stdin.encoding)
    return result if len(result) > 0 else default


def ask_user_password(prompt: str) -> str:
    """Read a password from the console."""
    return getpass.getpass(prompt + ": ")


def get_save_as_filename(defaultfilename: str,
                         defaultextension: str,
                         title: str = "Save As") -> str:
    """Provides a GUI "Save As" dialogue and returns the filename."""
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
    """Provides a GUI "Open" dialogue and returns the filename."""
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


def mkdir_p(path: str) -> None:
    """Makes a directory if it doesn't exist."""
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise
