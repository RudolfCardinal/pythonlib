#!/usr/bin/env python
# cardinal_pythonlib/formatting.py

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

**Formatting simple Python objects.**

"""

from typing import Any


# =============================================================================
# Number printing, e.g. for parity
# =============================================================================

def trunc_if_integer(n: Any) -> Any:
    """
    Truncates floats that are integers to their integer representation.
    That is, converts ``1.0`` to ``1``, etc.
    Otherwise, returns the starting value.
    Will raise an exception if the input cannot be converted to ``int``.
    """
    if n == int(n):
        return int(n)
    return n
