#!/usr/bin/env python
# cardinal_pythonlib/profile.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

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

**Profiling assistance functions.**

"""

import cProfile
from typing import Any, Callable


def do_cprofile(func: Callable, sort: str = "tottime") -> Callable:
    """
    Print profile stats to screen. To be used as a decorator for the function
    or method you want to profile. For example:

    .. code-block:: python

        profiled_func = do_cprofile(original_func)
        profiled_func(args_to_original_func)

    """

    def profiled_func(*args, **kwargs) -> Any:
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            profile.print_stats(sort=sort)

    return profiled_func
