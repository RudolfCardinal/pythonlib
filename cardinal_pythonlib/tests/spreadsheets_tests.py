#!/usr/bin/env python
# cardinal_pythonlib/tests/spreadsheets_tests.py

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

import unittest

from cardinal_pythonlib.spreadsheets import (
    column_lettering,
    colnum_zb_from_alphacol,
)


# =============================================================================
# Self-testing
# =============================================================================


class TestRoundingAndReversal(unittest.TestCase):
    def test_column_lettering(self) -> None:
        assert column_lettering(0) == "A"
        assert column_lettering(25) == "Z"
        assert column_lettering(26) == "AA"
        assert column_lettering(51) == "AZ"
        assert column_lettering(52) == "BA"
        for col_zb in range(200):
            alphacol = column_lettering(col_zb)
            assert colnum_zb_from_alphacol(alphacol) == col_zb
