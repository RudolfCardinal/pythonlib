#!/usr/bin/env python
# cardinal_pythonlib/randomness.py

"""
===============================================================================
    Copyright (C) 2009-2017 Rudolf Cardinal (rudolf@pobox.com).

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
"""

import base64
import os


def create_base64encoded_randomness(num_bytes: int) -> str:
    """
    Create num_bytes of random data.
    Result is encoded in a string with URL-safe base64 encoding.
    Used (for example) to generate session tokens.
    Which generator to use? See
        https://cryptography.io/en/latest/random-numbers/
    NOT: randbytes = M2Crypto.m2.rand_bytes(num_bytes)
    NOT: randbytes = Crypto.Random.get_random_bytes(num_bytes)
    """
    randbytes = os.urandom(num_bytes)  # YES
    return base64.urlsafe_b64encode(randbytes).decode('ascii')
