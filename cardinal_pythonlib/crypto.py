#!/usr/bin/env python
# cardinal_pythonlib/crypto.py

"""
===============================================================================

    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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

Support functions involving cryptography.

"""

# import Crypto.Random  # pip install pycrypto
import hashlib
import hmac
from typing import Any, Callable

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


# =============================================================================
# Base classes
# =============================================================================

class GenericHasher(object):
    """
    Abstract base class for a hasher.
    """
    def hash(self, raw: Any) -> str:
        """
        Returns a hash of its input.
        """
        raise NotImplementedError()


# =============================================================================
# Simple salted hashers.
# Note that these are vulnerable to attack: if an attacker knows a
# (message, digest) pair, it may be able to calculate another.
# See https://benlog.com/2008/06/19/dont-hash-secrets/ and
# http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.134.8430
# +++ You should use HMAC instead if the thing you are hashing is secret. +++
# =============================================================================

class GenericSaltedHasher(GenericHasher):
    """
    Generic representation of a hasher that stores a hash function and a salt.
    """
    def __init__(self, hashfunc: Callable[[bytes], Any], salt: str) -> None:
        """
        Args:
            hashfunc: hash function to use
            salt: salt to use (following UTF-8 encoding)
        """
        self.hashfunc = hashfunc
        self.salt_bytes = salt.encode('utf-8')

    def hash(self, raw: Any) -> str:
        raw_bytes = str(raw).encode('utf-8')
        return self.hashfunc(self.salt_bytes + raw_bytes).hexdigest()


class MD5Hasher(GenericSaltedHasher):
    """
    Salted hasher based on MD5.

    MD5 is cryptographically FLAWED; avoid.
    """
    def __init__(self, salt: str) -> None:
        super().__init__(hashlib.md5, salt)


class SHA256Hasher(GenericSaltedHasher):
    """
    Salted hasher based on SHA256.
    """
    def __init__(self, salt: str) -> None:
        super().__init__(hashlib.sha256, salt)


class SHA512Hasher(GenericSaltedHasher):
    """
    Salted hasher based on SHA512.
    """
    def __init__(self, salt: str) -> None:
        super().__init__(hashlib.sha512, salt)


# =============================================================================
# HMAC hashers. Better, if what you are hashing is secret.
# =============================================================================

class GenericHmacHasher(GenericHasher):
    """
    Generic representation of a hasher that hashes things via an HMAC
    (a hash-based message authentication code).
    See https://en.wikipedia.org/wiki/HMAC
    """
    def __init__(self, digestmod: Any, key: str) -> None:
        """
        Args:
            digestmod: see :func:`hmac.HMAC.__init__`
            key: cryptographic key to use
        """
        self.key_bytes = key.encode('utf-8')
        self.digestmod = digestmod

    def hash(self, raw: Any) -> str:
        """
        Returns the hex digest of a HMAC-encoded version of the input.
        """
        raw_bytes = str(raw).encode('utf-8')
        hmac_obj = hmac.new(key=self.key_bytes, msg=raw_bytes,
                            digestmod=self.digestmod)
        return hmac_obj.hexdigest()


class HmacMD5Hasher(GenericHmacHasher):
    """
    HMAC hasher based on MD5.
    (Even though MD5 is insecure, HMAC-MD5 is better. See Bellare M, Canetti R,
    Krawcyk H. Keying hash functions for message authentication. Lect. Notes
    Comput. Sci. Adv. Cryptol. - Crypto 96 Proc. 1996; 1109: 1–15.)
    """
    def __init__(self, key: str) -> None:
        super().__init__(hashlib.md5, key)


class HmacSHA256Hasher(GenericHmacHasher):
    """
    HMAC hasher based on SHA256.
    """
    def __init__(self, key: str) -> None:
        super().__init__(hashlib.sha256, key)


class HmacSHA512Hasher(GenericHmacHasher):
    """
    HMAC hasher based on SHA512.
    """
    def __init__(self, key: str) -> None:
        super().__init__(hashlib.sha512, key)


# =============================================================================
# Testing functions/notes
# =============================================================================

_ = """
import hashlib
from six.moves import range

class MD5Hasher(object):
    def __init__(self, salt):
        self.salt = salt
    def hash(self, raw):
        raw = str(raw)
        return hashlib.md5(self.salt + raw).hexdigest()

MAX_PID_STR = "9" * 10  # e.g. NHS numbers are 10-digit
MAX_PID_NUM = int(MAX_PID_STR)
# sets are MUCH, MUCH faster than lists for "have-I-seen-it" tests
hasher = MD5Hasher("dummysalt")
used_hashes = set()
for i in range(MAX_PID_NUM):
    if i % 1000000 == 0:
        print("... " + str(i))
    x = hasher.hash(i)
    if x in used_hashes:
        raise Exception("Collision! i={}".format(i))
    used_hashes.add(x)

# This gets increasingly slow but is certainly fine up to
#     282,000,000
# and we want to test
#   9,999,999,999
# Anyway, other people have done the work:
#   http://crypto.stackexchange.com/questions/15873
# ... and the value is expected to be at least 2^64, whereas an NHS number
# is less than 2^34 -- from math.log(9999999, 2).

"""
