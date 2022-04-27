#!/usr/bin/env python
# cardinal_pythonlib/tests/interval_tests.py

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

import datetime
import logging
import unittest

from cardinal_pythonlib.interval import Interval

log = logging.getLogger(__name__)


# =============================================================================
# Unit testing
# =============================================================================


class TestInterval(unittest.TestCase):
    """
    Unit tests.
    """

    def test_interval(self) -> None:
        a = datetime.datetime(2015, 1, 1)
        log.debug(f"a = {a!r}")
        b = datetime.datetime(2015, 1, 6)
        log.debug(f"b = {b!r}")
        i = Interval(a, b)
        log.debug(f"i = {i!r}")
        j = i + datetime.timedelta(hours=3)
        log.debug(f"j = {j!r}")
        cut = i.cut(datetime.datetime(2015, 1, 3))
        log.debug(f"cut = {cut!r}")
