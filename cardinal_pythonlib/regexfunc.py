#!/usr/bin/env python
# cardinal_pythonlib/regexfunc.py

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

**Regular expression support functions.**

"""

from typing import Match, Optional, Pattern


# =============================================================================
# Class to store last match of compiled regex
# =============================================================================
# Based on http://stackoverflow.com/questions/597476/how-to-concisely-cascade-through-multiple-regex-statements-in-python  # noqa

class CompiledRegexMemory(object):
    """
    Class to store last match of compiled regex.
    
    Once you have called :func:`match` or :func:`search`, the attribute
    :attr:`last_match` contains the last match, and ``group(n)`` returns the
    *n*\ th group of that last match.
    
    Based on
    http://stackoverflow.com/questions/597476/how-to-concisely-cascade-through-multiple-regex-statements-in-python.
    """  # noqa
    def __init__(self) -> None:
        self.last_match = None  # type: Match

    def match(self, compiled_regex: Pattern, text: str) -> Match:
        self.last_match = compiled_regex.match(text)
        return self.last_match

    def search(self, compiled_regex: Pattern, text: str) -> Match:
        self.last_match = compiled_regex.search(text)
        return self.last_match

    def group(self, n: int) -> Optional[str]:
        if not self.last_match:
            return None
        return self.last_match.group(n)
