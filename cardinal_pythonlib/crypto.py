#!/usr/bin/env python
# cardinal_pythonlib/crypto.py

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

**Support functions involving cryptography.**

"""

# The following requires a C compiler, so we don't have it in our standard
# requirements. However, it is vital for this module.

# noinspection PyUnresolvedReferences
import bcrypt  # pip install bcrypt; see https://pypi.org/project/bcrypt/


# =============================================================================
# bcrypt
# =============================================================================

BCRYPT_DEFAULT_LOG_ROUNDS = 12  # bcrypt default; work factor is 2^this.


def hash_password(plaintextpw: str,
                  log_rounds: int = BCRYPT_DEFAULT_LOG_ROUNDS) -> str:
    """
    Makes a hashed password (using a new salt) using ``bcrypt``.

    The hashed password includes the salt at its start, so no need to store a
    separate salt.
    """
    salt = bcrypt.gensalt(log_rounds)  # optional parameter governs complexity
    hashedpw = bcrypt.hashpw(plaintextpw, salt)
    return hashedpw


def is_password_valid(plaintextpw: str, storedhash: str) -> bool:
    """
    Checks if a plaintext password matches a stored hash.

    Uses ``bcrypt``. The stored hash includes its own incorporated salt.
    """
    # Upon CamCOPS from MySQL 5.5.34 (Ubuntu) to 5.1.71 (CentOS 6.5), the
    # VARCHAR was retrieved as Unicode. We needed to convert that to a str.
    # For Python 3 compatibility, we just str-convert everything, avoiding the
    # unicode keyword, which no longer exists.
    if storedhash is None:
        storedhash = ""
    storedhash = str(storedhash)
    if plaintextpw is None:
        plaintextpw = ""
    plaintextpw = str(plaintextpw)
    try:
        h = bcrypt.hashpw(plaintextpw, storedhash)
    except ValueError:  # e.g. ValueError: invalid salt
        return False
    return h == storedhash
