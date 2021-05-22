#!/usr/bin/env python
# cardinal_pythonlib/module_version.py

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

**Find a Python module's version (across Python versions)**

See

- https://stackoverflow.com/questions/710609/checking-a-python-module-version-at-runtime
- https://stackoverflow.com/questions/20180543/how-to-check-version-of-python-modules

"""  # noqa

# =============================================================================
# Imports
# =============================================================================

import sys

from semantic_version import Version

# noinspection PyUnresolvedReferences
import cardinal_pythonlib.ensure_test_executed_correctly

if sys.version_info > (3, 8):
    # Python 3.8 or higher
    # noinspection PyCompatibility
    from importlib.metadata import version
else:
    try:
        from importlib_metadata import version
    except ImportError:
        raise


# =============================================================================
# Report Python module versions
# =============================================================================

def module_version_string(module_name: str) -> str:
    """
    The string version of a Python module.

    Will raise :exc:`PackageNotFoundError` if not found.
    """
    return version(module_name)


def module_semantic_version(module_name: str) -> Version:
    """
    The semantic version of a Python module.
    """
    version_string = module_version_string(module_name)  # may raise PackageNotFoundError  # noqa
    return Version(version_string)  # may raise ValueError
