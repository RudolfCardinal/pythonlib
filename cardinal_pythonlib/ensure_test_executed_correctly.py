#!/usr/bin/env python
# cardinal_pythonlib/module_version.py

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

**Ensure that a library module is executed properly, and not via a way that
breaks imports.**

"""

try:
    # we want the stdlib email package!
    from email import message_from_string  # noqa: F401
except ImportError:
    raise ImportError(
        "A test of importing 'email' has found "
        "cardinal_pythonlib/email/__init__.py, not the email package from "
        "stdlib. You are probably running a cardinal_pythonlib file directly, "
        "e.g. with 'python somefile.py' or '/path/somefile.py'. Instead, use "
        "'python -m cardinal_pythonlib.somefile'."
    )
