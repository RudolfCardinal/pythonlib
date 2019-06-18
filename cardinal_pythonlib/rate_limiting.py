#!/usr/bin/env python
# cardinal_pythonlib/rate_limiting.py

"""
===============================================================================

    Original code copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).

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

**Rate-limiting functions.**

"""

import logging
import time
from typing import Any, Callable, Optional

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger


log = logging.getLogger(__name__)
FuncType = Callable[..., Any]


def rate_limited(max_per_second: Optional[int]) \
        -> Callable[[FuncType], FuncType]:
    """
    Returns a function that rate-limits another function to the specified
    frequency. Can be used as a decorator, e.g.

    .. code-block:: python

        @rate_limited(2)
        def do_something_max_2hz():
            print("tick...")

        for i in range(10):
            do_something_max_2hz()

    or dynamically:

    .. code-block:: python

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
            elapsed = time.clock() - last_time_called
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            retval = func(*args, **kwargs)
            last_time_called = time.clock()
            return retval

        return rate_limited_function

    return decorate


@rate_limited(2)
def _test_print_2hz(num: int) -> None:
    log.info("_test_print_2hz: {}".format(num))


@rate_limited(5)
def _test_print_5hz(num: int) -> None:
    log.info("_test_print_5hz: {}".format(num))


def _test_print(num: int) -> None:
    log.info("_test_print: {}".format(num))


def test_rate_limiter() -> None:
    """
    Test the rate-limiting functions.
    """
    n = 10
    log.warning("Via decorator, 2 Hz")
    for i in range(1, n + 1):
        _test_print_2hz(i)
    log.warning("Via decorator, 5 Hz")
    for i in range(1, n + 1):
        _test_print_5hz(i)
    log.warning("Created dynamically, 10 Hz")
    tenhz = rate_limited(10)(_test_print)
    for i in range(1, n + 1):
        tenhz(i)
    log.warning("Created dynamically, unlimited")
    unlimited = rate_limited(None)(_test_print)
    for i in range(1, n + 1):
        unlimited(i)


if __name__ == "__main__":
    main_only_quicksetup_rootlogger(level=logging.DEBUG)
    test_rate_limiter()
