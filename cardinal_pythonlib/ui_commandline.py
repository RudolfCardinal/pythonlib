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

**Support functions for user interaction -- command line only.**

Does not need tkinter.

"""

import getpass
from typing import Optional


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
