#!/usr/bin/env python
# cardinal_pythonlib/email/tests/sendmail_tests.py

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

import unittest

from cardinal_pythonlib.email.sendmail import is_email_valid


class TestIsEmailValid(unittest.TestCase):
    def test_is_email_valid(self) -> None:
        good_addresses = [
            "x@somewhere.com",
            "a+b@somewhere.else",
            "fish123@blah.com",
        ]
        bad_addresses = [
            "xyz",
            "thing@blah.com@blah.com",
            "thing,with_comma@somewhere.co.uk",
            "person@place.fullstop.",
        ]
        for good in good_addresses:
            self.assertTrue(
                is_email_valid(good),
                f"Good e-mail being flagged as bad: {good!r}"
            )
        for bad in bad_addresses:
            self.assertFalse(
                is_email_valid(bad),
                f"Bad e-mail being flagged as good: {bad!r}"
            )
