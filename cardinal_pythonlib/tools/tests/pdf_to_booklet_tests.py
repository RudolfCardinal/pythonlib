#!/usr/bin/env python
# cardinal_pythonlib/tools/tests/pdf_to_booklet_tests.py

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

**Unit tests.**

"""

import logging
import unittest

from cardinal_pythonlib.tools.pdf_to_booklet import page_sequence

log = logging.getLogger(__name__)


# =============================================================================
# Unit testing
# =============================================================================

class TestPdfToBooklet(unittest.TestCase):
    """
    Unit tests.
    """
    def test_sequence(self) -> None:
        for n_sheets in range(1, 8 + 1):
            log.info("{!r}", page_sequence(n_sheets=n_sheets, one_based=True))
