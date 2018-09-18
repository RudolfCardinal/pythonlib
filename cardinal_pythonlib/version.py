#!/usr/bin/env python
# cardinal_pythonlib/version.py

"""
===============================================================================

    Original code copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Functions to check the version of this library.**

"""

from semantic_version import Version

from cardinal_pythonlib.version_string import VERSION_STRING as VERSION

CARDINAL_PYTHONLIB_VERSION = Version(VERSION)


def _get_version_failure_msg(op: str, version_str: str) -> str:
    return "Requested {op}{v} but cardinal_pythonlib=={cpv}".format(
        op=op, v=version_str, cpv=VERSION
    )


def assert_version_lt(version_str: str) -> None:
    """
    Asserts that the cardinal_pythonlib version is less than the value supplied
    (as a semantic version string, e.g. "1.0.2").
    """
    assert CARDINAL_PYTHONLIB_VERSION < Version(version_str), (
        _get_version_failure_msg("<", version_str)
    )


def assert_version_le(version_str: str) -> None:
    """
    Asserts that the cardinal_pythonlib version is less than or equal to the
    value supplied (as a semantic version string, e.g. "1.0.2").
    """
    assert CARDINAL_PYTHONLIB_VERSION <= Version(version_str), (
        _get_version_failure_msg("<=", version_str)
    )


def assert_version_eq(version_str: str) -> None:
    """
    Asserts that the cardinal_pythonlib version is equal to the value supplied
    (as a semantic version string, e.g. "1.0.2").
    """
    assert CARDINAL_PYTHONLIB_VERSION == Version(version_str), (
        _get_version_failure_msg("==", version_str)
    )


def assert_version_ge(version_str: str) -> None:
    """
    Asserts that the cardinal_pythonlib version is greater than or equal to the
    value supplied (as a semantic version string, e.g. "1.0.2").
    """
    assert CARDINAL_PYTHONLIB_VERSION >= Version(version_str), (
        _get_version_failure_msg(">=", version_str)
    )


def assert_version_gt(version_str: str) -> None:
    """
    Asserts that the cardinal_pythonlib version is greater than the value
    supplied (as a semantic version string, e.g. "1.0.2").
    """
    assert CARDINAL_PYTHONLIB_VERSION > Version(version_str), (
        _get_version_failure_msg(">", version_str)
    )
