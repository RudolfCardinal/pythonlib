#!/usr/bin/env python
# cardinal_pythonlib/cmdline.py

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
"""

import re
# import shlex
import subprocess
import sys
from typing import List, Union


def cmdline_split(s: str, platform: Union[int, str] = 'this') -> List[str]:
    """
    https://stackoverflow.com/questions/33560364/python-windows-parsing-command-lines-with-shlex

    Multi-platform variant of shlex.split() for command-line splitting.
    For use with subprocess, for argv injection etc. Using fast REGEX.

    platform: 'this' = auto from current platform;
              1 = POSIX;
              0 = Windows/CMD
              (other values reserved)
    """
    if platform == 'this':
        platform = (sys.platform != 'win32')  # RNC: includes 64-bit Windows
    if platform == 1:  # POSIX
        re_cmd_lex = r'''"((?:\\["\\]|[^"])*)"|'([^']*)'|(\\.)|(&&?|\|\|?|\d?\>|[<])|([^\s'"\\&|<>]+)|(\s+)|(.)'''  # noqa
    elif platform == 0:  # Windows/CMD
        re_cmd_lex = r'''"((?:""|\\["\\]|[^"])*)"?()|(\\\\(?=\\*")|\\")|(&&?|\|\|?|\d?>|[<])|([^\s"&|<>]+)|(\s+)|(.)'''  # noqa
    else:
        raise AssertionError('unknown platform %r' % platform)

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
            word = qs.replace('\\"', '"').replace('\\\\', '\\')
            if platform == 0:
                word = word.replace('""', '"')
        else:
            word = qss   # may be even empty; must be last

        accu = (accu or '') + word

    if accu is not None:
        args.append(accu)

    return args


def cmdline_quote(args: List[str]) -> str:
    # if platform == 'this':
    #     platform = (sys.platform != 'win32')  includes 64-bit Windows
    # if platform == 1:  # POSIX
    #     return " ".join(shlex.quote(x) for x in args).replace("\n", r"\n")
    # elif platform == 0:  # Windows/CMD
    return subprocess.list2cmdline(args)
