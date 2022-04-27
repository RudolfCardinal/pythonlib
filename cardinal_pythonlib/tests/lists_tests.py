#!/usr/bin/env python
# cardinal_pythonlib/tests/lists_tests.py

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

from cardinal_pythonlib.lists import delete_elements_by_index


class TestListDelete(unittest.TestCase):
    def test_list_del(self) -> None:
        original_x = [0, 1, 2, 3]

        x = original_x.copy()
        self.assertRaises(IndexError, delete_elements_by_index, x, [4])
        delete_elements_by_index(x, [3, 1])
        self.assertEqual(x, [0, 2])

        x = original_x.copy()
        delete_elements_by_index(x, [3])
        self.assertEqual(x, [0, 1, 2])
