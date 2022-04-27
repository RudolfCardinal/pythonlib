#!/usr/bin/env python
# cardinal_pythonlib/randomness.py

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

**Random number generation.**

"""

import base64
import os
from random import random as random_random
import secrets
import string


# =============================================================================
# Creating random strings
# =============================================================================


def create_base64encoded_randomness(num_bytes: int) -> str:
    """
    Create and return ``num_bytes`` of random data.

    The result is encoded in a string with URL-safe ``base64`` encoding.

    Used (for example) to generate session tokens.

    Which generator to use? See
    https://cryptography.io/en/latest/random-numbers/.

    Do NOT use these methods:

    .. code-block:: python

        randbytes = M2Crypto.m2.rand_bytes(num_bytes) # NO!
        randbytes = Crypto.Random.get_random_bytes(num_bytes) # NO!

    Instead, do this:

    .. code-block:: python

        randbytes = os.urandom(num_bytes)  # YES
    """
    randbytes = os.urandom(num_bytes)  # YES
    return base64.urlsafe_b64encode(randbytes).decode("ascii")


def generate_random_string(length: int, characters: str = None) -> str:
    """
    Generates a random string of the specified length.
    """
    characters = characters or (
        string.ascii_letters + string.digits + string.punctuation
    )
    # We use secrets.choice() rather than random.choices() as it's better
    # for security/cryptography purposes.
    return "".join(secrets.choice(characters) for _ in range(length))


# =============================================================================
# Coin flips
# =============================================================================


def coin(p: float) -> bool:
    """
    Flips a biased coin; returns ``True`` or ``False``, with the specified
    probability being that of ``True``.
    """
    # Slower code:

    # assert 0 <= p <= 1
    # r = random.random()  # range [0.0, 1.0), i.e. 0 <= r < 1
    # return r < p

    # Check edge cases:
    # - if p == 0, impossible that r < p, since r >= 0
    # - if p == 1, always true that r < p, since r < 1

    # Faster code:

    return random_random() < p


# =============================================================================
# Testing
# =============================================================================


def _test_coin() -> None:
    """
    Tests the :func:`coin` function.
    """
    probabilities = [0, 0.25, 0.5, 0.75, 1]
    n_values = [10, 1000, 1000000]
    for p in probabilities:
        for n in n_values:
            coins = [1 if coin(p) else 0 for _ in range(n)]
            s = sum(coins)
            print(f"coin: p = {p}, n = {n} -> {s} true")


if __name__ == "__main__":
    _test_coin()
