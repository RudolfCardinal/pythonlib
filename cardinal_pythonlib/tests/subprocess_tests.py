#!/usr/bin/env python
# cardinal_pythonlib/tests/subprocess_tests.py

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

from typing import List
import unittest

from cardinal_pythonlib.subproc import run_multiple_processes


class TestSubprocess(unittest.TestCase):
    def test_limited_launch(self) -> None:
        """
        Monitor this with:

        .. code-block:: bash

            watch --interval 1 "ps aux | grep sleep | grep -v grep"
        """
        n_total = 8
        max_workers = n_total // 2
        seconds_per_process = n_total
        args_list = []  # type: List[List[str]]
        for i in range(1, n_total + 1):
            # So that we can distinguish each one, we use e.g. "sleep 1 16",
            # "sleep 2 15", etc. -- each has the same total duration.
            args_list.append(["sleep", str(i), str(seconds_per_process - i)])
        run_multiple_processes(args_list, max_workers=max_workers)
