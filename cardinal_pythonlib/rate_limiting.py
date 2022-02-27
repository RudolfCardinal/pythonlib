#!/usr/bin/env python
# cardinal_pythonlib/rate_limiting.py

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

**Rate-limiting functions.**

"""

import logging
from time import perf_counter, sleep
from typing import Any, Callable, Optional, Union

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger


log = logging.getLogger(__name__)
FuncType = Callable[..., Any]


def rate_limited(max_per_second: Optional[Union[int, float]]) \
        -> Callable[[FuncType], FuncType]:
    """
    Returns a function that rate-limits another function to the specified
    frequency. Can be used as a decorator, e.g.

    .. code-block:: python

        from cardinal_pythonlib.rate_limiting import rate_limited

        @rate_limited(2)
        def do_something_max_2hz():
            print("tick...")

        for i in range(10):
            do_something_max_2hz()

    or dynamically:

    .. code-block:: python

        from cardinal_pythonlib.rate_limiting import rate_limited

        def do_something():
            print("tick...")

        limited = rate_limited(2)(do_something)
        for i in range(10):
            limited()

    Args:
        max_per_second:
            maximum number of calls per second to permit, or ``None`` for no
            limit

    Returns:
        a function that takes a function argument

    Based on
    https://www.gregburek.com/2011/12/05/rate-limiting-with-decorators/, with
    minor modifications.
    """
    assert max_per_second is None or max_per_second > 0
    min_interval = None  # type: Optional[float]
    if max_per_second is not None:
        min_interval = 1.0 / float(max_per_second)

    def decorate(func: FuncType) -> FuncType:
        if max_per_second is None:
            return func  # no rate limiting
        last_time_called = 0.0

        def rate_limited_function(*args, **kwargs) -> Any:
            nonlocal last_time_called
            elapsed = perf_counter() - last_time_called
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                sleep(left_to_wait)
            retval = func(*args, **kwargs)
            last_time_called = perf_counter()
            return retval

        return rate_limited_function

    return decorate
