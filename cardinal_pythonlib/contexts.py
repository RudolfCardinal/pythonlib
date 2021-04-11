#!/usr/bin/env python
# cardinal_pythonlib/contexts.py

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

**Context manager assistance.**

"""

import contextlib


@contextlib.contextmanager
def dummy_context_mgr():
    """
    We might be using Python 3.6 which doesn't have ``contextlib.nullcontext``.
    Hence this.

    - https://stackoverflow.com/questions/27803059/conditional-with-statement-in-python
    - See also
      https://stackoverflow.com/questions/893333/multiple-variables-in-a-with-statement
    """  # noqa
    yield None
