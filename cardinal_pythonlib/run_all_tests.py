#!/usr/bin/env python
# cardinal_pythonlib/run_all_tests.py

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

**Run all tests across the library.**

"""

import subprocess
import os


THIS_DIR = os.path.dirname(os.path.realpath(__file__))


def run_all_unit_tests() -> None:
    cmdargs = [
        # "python", "-m", "unittest", "discover", "-s", THIS_DIR, "-p", "*.py"
        "pytest", THIS_DIR
    ]
    subprocess.check_call(cmdargs)


if __name__ == "__main__":
    run_all_unit_tests()
