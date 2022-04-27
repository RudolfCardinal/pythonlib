#!/usr/bin/env python
# cardinal_pythonlib/tests/rate_limiting_tests.py

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

**Unit tests.**

"""

import logging
import unittest

from cardinal_pythonlib.rate_limiting import rate_limited

log = logging.getLogger(__name__)


@rate_limited(2)
def _test_print_2hz(num: int) -> None:
    log.info(f"_test_print_2hz: {num}")


@rate_limited(5)
def _test_print_5hz(num: int) -> None:
    log.info(f"_test_print_5hz: {num}")


def _test_print(num: int) -> None:
    log.info(f"_test_print: {num}")


class RateLimitingTests(unittest.TestCase):
    @staticmethod
    def test_rate_limiter() -> None:
        """
        Test the rate-limiting functions.
        """
        n = 10
        log.info("Via decorator, 2 Hz")
        for i in range(1, n + 1):
            _test_print_2hz(i)
        log.info("Via decorator, 5 Hz")
        for i in range(1, n + 1):
            _test_print_5hz(i)
        log.info("Created dynamically, 10 Hz")
        tenhz = rate_limited(10)(_test_print)
        for i in range(1, n + 1):
            tenhz(i)
        log.info("Created dynamically, unlimited")
        unlimited = rate_limited(None)(_test_print)
        for i in range(1, n + 1):
            unlimited(i)
