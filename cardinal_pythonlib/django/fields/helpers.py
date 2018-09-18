#!/usr/bin/env python
# cardinal_pythonlib/django/fields/helpers.py

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

**Helper functions for Django fields.**

"""

from typing import Iterable, Tuple


# =============================================================================
# Field choice assistance
# =============================================================================

def valid_choice(strvalue: str, choices: Iterable[Tuple[str, str]]) -> bool:
    """
    Checks that value is one of the valid option in choices, where choices
    is a list/tuple of 2-tuples (option, description).

    Note that parameters sent by URLconf are always strings
    (https://docs.djangoproject.com/en/1.8/topics/http/urls/)
    but Python is happy with a string-to-integer-PK lookup, e.g.

    .. code-block:: python

        Study.objects.get(pk=1)
        Study.objects.get(pk="1")  # also works

    Choices can be non-string, though, so we compare against a string version
    of the choice.
    """
    return strvalue in [str(x[0]) for x in choices]


def choice_explanation(value: str, choices: Iterable[Tuple[str, str]]) -> str:
    """
    Returns the explanation associated with a Django choice tuple-list.
    """
    for k, v in choices:
        if k == value:
            return v
    return ''
