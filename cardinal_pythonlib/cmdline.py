#!/usr/bin/env python
# cardinal_pythonlib/cmdline.py

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

**Functions for manipulating command-line parameters.**

"""

import re
# import shlex
import subprocess
import sys
from typing import List, Union


def cmdline_split(s: str, platform: Union[int, str] = 'this') -> List[str]:
    """
    As per
    https://stackoverflow.com/questions/33560364/python-windows-parsing-command-lines-with-shlex.

    Multi-platform variant of ``shlex.split()`` for command-line splitting.
    For use with ``subprocess``, for ``argv`` injection etc. Using fast REGEX.

    Args:
        s:
            string to split
        platform:
            - ``'this'`` = auto from current platform;
            - ``1`` = POSIX;
            - ``0`` = Windows/CMD
            - (other values reserved)
    """  # noqa
    if platform == 'this':
        platform = (sys.platform != 'win32')  # RNC: includes 64-bit Windows

    if platform == 1:  # POSIX
        re_cmd_lex = r'''"((?:\\["\\]|[^"])*)"|'([^']*)'|(\\.)|(&&?|\|\|?|\d?\>|[<])|([^\s'"\\&|<>]+)|(\s+)|(.)'''  # noqa
    elif platform == 0:  # Windows/CMD
        re_cmd_lex = r'''"((?:""|\\["\\]|[^"])*)"?()|(\\\\(?=\\*")|\\")|(&&?|\|\|?|\d?>|[<])|([^\s"&|<>]+)|(\s+)|(.)'''  # noqa
    else:
        raise AssertionError(f"unknown platform {platform!r}")

    args = []
    accu = None   # collects pieces of one arg
    for qs, qss, esc, pipe, word, white, fail in re.findall(re_cmd_lex, s):
        if word:
            pass   # most frequent
        elif esc:
            word = esc[1]
        elif white or pipe:
            if accu is not None:
                args.append(accu)
            if pipe:
                args.append(pipe)
            accu = None
            continue
        elif fail:
            raise ValueError("invalid or incomplete shell string")
        elif qs:
            word = qs.replace(r'\"', '"').replace(r'\\', '\\')
            # ... raw strings can't end in single backslashes;
            # https://stackoverflow.com/questions/647769/why-cant-pythons-raw-string-literals-end-with-a-single-backslash  # noqa
            if platform == 0:
                word = word.replace('""', '"')
        else:
            word = qss   # may be even empty; must be last

        accu = (accu or '') + word

    if accu is not None:
        args.append(accu)

    return args


def cmdline_quote_posix(seq: List[str]) -> str:
    """
    Quotes arguments for POSIX, producing a single string suitable for
    copying/pasting.

    Based on subprocess.list2cmdline().
    """
    result = []  # type: List[str]
    for arg in seq:
        bs_buf = []  # type: List[str]

        # Add a space to separate this argument from the others
        if result:
            result.append(' ')

        # Modified here: quote arguments with "*"
        needquote = (" " in arg) or ("\t" in arg) or ("*" in arg) or not arg
        if needquote:
            result.append('"')

        for c in arg:
            if c == '\\':
                # Don't know if we need to double yet.
                bs_buf.append(c)
            elif c == '"':
                # Double backslashes.
                result.append('\\' * len(bs_buf) * 2)
                bs_buf = []
                result.append('\\"')
            else:
                # Normal char
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(c)

        # Add remaining backslashes, if any.
        if bs_buf:
            result.extend(bs_buf)

        if needquote:
            result.extend(bs_buf)
            result.append('"')

    return ''.join(result)


def cmdline_quote(args: List[str], platform: Union[int, str] = 'this') -> str:
    """
    Convert a list of command-line arguments to a suitably quoted command-line
    string that should be copy/pastable into a comand prompt.
    """
    if platform == 'this':
        platform = (sys.platform != 'win32')  # RNC: includes 64-bit Windows

    if platform == 1:  # POSIX
        return cmdline_quote_posix(args)
    elif platform == 0:  # Windows/CMD
        return subprocess.list2cmdline(args)
    else:
        raise AssertionError(f"unknown platform {platform!r}")
