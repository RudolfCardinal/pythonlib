#!/usr/bin/env python
# cardinal_pythonlib/typetests.py

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

from typing import Any, Iterable


# =============================================================================
# Testers/validators
# =============================================================================

def is_integer(s: Any) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def raise_if_attr_blank(obj: Any, attrs: Iterable[str]) -> None:
    for a in attrs:
        value = getattr(obj, a)
        if value is None or value is "":
            raise Exception("Blank attribute: {}".format(a))


# =============================================================================
# bool
# =============================================================================

def is_false(x: Any) -> bool:
    """Positively false? Evaluates: not x and x is not None."""
    # beware: "0 is False" evaluates to False -- AVOID "is False"!
    # ... but "0 == False" evaluates to True
    # http://stackoverflow.com/questions/3647692/
    # ... but comparisons to booleans with "==" fail PEP8:
    # http://legacy.python.org/dev/peps/pep-0008/
    # ... so use e.g. "bool(x)" or "x" or "not x"
    # http://google-styleguide.googlecode.com/svn/trunk/pyguide.html?showone=True/False_evaluations#True/False_evaluations  # noqa
    return not x and x is not None
