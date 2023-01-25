#!/usr/bin/env python
# cardinal_pythonlib/hash.py

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

**Hash functions**

In general, consider these hash functions:

- :func:`hash64`, using MurmurHash3 to provide a 64-bit integer: for fast
  INSECURE COMPARISON operations.
- an ``Hmac*`` class for SECURE cryptographic hashes.

Regarding None/NULL values (in CRATE):

- For difference detection, it may be helpful to be able to compare a standard
  hash, in which case ``somehash(None) == somehash("None") ==
  'abcdefsomething'``.

- It is vital not to hash NULL patient IDs, though: for example, two different
  patients without an NHS number must not be equated by comparison on a hash
  of the (NULL) NHS number.

- For anonymisation, this is handled in these functions:

  .. code-block:: none

    crate_anon/anonymise/anonymise.py / process_table()
    -> crate_anon/anonymise/configfiles.py / Config.encrypt_master_pid()
    -> crate_anon/anonymise/patient.py / Patient.get_rid
        ... via PatientInfo.rid
        ... to Config.encrypt_primary_pid()
"""

import hashlib
import hmac
import sys
from typing import Any, Callable, Tuple, Union

from sqlalchemy.sql.sqltypes import String, TypeEngine

try:
    # noinspection PyPackageRequirements
    import mmh3
except ImportError:
    mmh3 = None

# try:
#     import xxhash
#     pyhashxx = None
# except ImportError:
#     xxhash = None
#     import pyhashxx


# https://docs.python.org/3/library/platform.html#platform.architecture
IS_64_BIT = sys.maxsize > 2**32
TIMING_HASH = "hash"


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

    def output_length(self) -> int:
        """
        Returns the length of the hashes produced by this hasher.
        """
        return len(self.hash("dummytext"))

    def sqla_column_type(self) -> TypeEngine:
        """
        Returns a SQLAlchemy :class:`Column` type instance, specifically
        ``String(length=self.output_length())``.
        """
        return String(length=self.output_length())


# =============================================================================
# Simple salted hashers.
# =============================================================================


class GenericSaltedHasher(GenericHasher):
    """
    Generic representation of a simple salted hasher that stores a hash
    function and a salt.

    Note that these are vulnerable to attack: if an attacker knows a
    ``(message, digest)`` pair, it may be able to calculate another.
    See https://benlog.com/2008/06/19/dont-hash-secrets/ and
    https://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.134.8430

    **You should use HMAC instead if the thing you are hashing is secret.**
    """

    def __init__(self, hashfunc: Callable[[bytes], Any], salt: str) -> None:
        """
        Args:
            hashfunc: hash function to use
            salt: salt to use (following UTF-8 encoding)
        """
        self.hashfunc = hashfunc
        self.salt_bytes = salt.encode("utf-8")

    def hash(self, raw: Any) -> str:
        raw_bytes = str(raw).encode("utf-8")
        return self.hashfunc(self.salt_bytes + raw_bytes).hexdigest()


class MD5Hasher(GenericSaltedHasher):
    """
    Salted hasher based on MD5.

    MD5 is cryptographically FLAWED; avoid using it or this class.
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

    HMAC hashers are the thing to use if what you are hashing is secret.
    """

    def __init__(self, digestmod: Any, key: str) -> None:
        """
        Args:
            digestmod: see :func:`hmac.HMAC.__init__`
            key: cryptographic key to use
        """
        self.key_bytes = str(key).encode("utf-8")
        self.digestmod = digestmod

    def hash(self, raw: Any) -> str:
        """
        Returns the hex digest of a HMAC-encoded version of the input.
        """
        raw_bytes = str(raw).encode("utf-8")
        hmac_obj = hmac.new(
            key=self.key_bytes, msg=raw_bytes, digestmod=self.digestmod
        )
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
# Hash factory
# =============================================================================


class HashMethods(object):
    MD5 = "MD5"
    SHA256 = "SHA256"
    SHA512 = "SHA512"
    HMAC_MD5 = "HMAC_MD5"
    HMAC_SHA256 = "HMAC_SHA256"
    HMAC_SHA512 = "HMAC_SHA512"


def make_hasher(hash_method: str, key: str) -> GenericHasher:
    hash_method = hash_method.upper()
    if hash_method in (
        HashMethods.MD5,
        HashMethods.SHA256,
        HashMethods.SHA512,
    ):
        raise ValueError(
            f"Non-HMAC hashers are deprecated for security reasons. You are "
            f"trying to use: {hash_method}"
        )
    if hash_method == HashMethods.HMAC_MD5:
        return HmacMD5Hasher(key)
    elif hash_method == HashMethods.HMAC_SHA256 or not hash_method:
        return HmacSHA256Hasher(key)
    elif hash_method == HashMethods.HMAC_SHA512:
        return HmacSHA512Hasher(key)
    else:
        raise ValueError(f"Unknown value for hash_method: {hash_method}")


def get_longest_supported_hasher_output_length() -> int:
    dummyhash = make_hasher(HashMethods.HMAC_SHA512, "dummysalt")
    return dummyhash.output_length()


# =============================================================================
# Testing functions/notes relating to hashing
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
#   https://crypto.stackexchange.com/questions/15873
# ... and the value is expected to be at least 2^64, whereas an NHS number
# is less than 2^34 -- from math.log(9999999, 2).

"""


# =============================================================================
# Support functions
# =============================================================================


def to_bytes(data: Any) -> bytearray:
    """
    Convert anything to a ``bytearray``.

    See

    - https://stackoverflow.com/questions/7585435/best-way-to-convert-string-to-bytes-in-python-3
    - https://stackoverflow.com/questions/10459067/how-to-convert-my-bytearrayb-x9e-x18k-x9a-to-something-like-this-x9e-x11
    """  # noqa
    if isinstance(data, int):
        return bytearray([data])
    return bytearray(data, encoding="latin-1")


def to_str(data: Any) -> str:
    """
    Convert anything to a ``str``.
    """
    return str(data)


def twos_comp_to_signed(val: int, n_bits: int) -> int:
    """
    Convert a "two's complement" representation (as an integer) to its signed
    version.

    Args:
        val: positive integer representing a number in two's complement format
        n_bits: number of bits (which must reflect a whole number of bytes)

    Returns:
        signed integer

    See https://stackoverflow.com/questions/1604464/twos-complement-in-python

    """
    assert n_bits % 8 == 0, "Must specify a whole number of bytes"
    n_bytes = n_bits // 8
    b = val.to_bytes(n_bytes, byteorder=sys.byteorder, signed=False)
    return int.from_bytes(b, byteorder=sys.byteorder, signed=True)


def signed_to_twos_comp(val: int, n_bits: int) -> int:
    """
    Convert a signed integer to its "two's complement" representation.

    Args:
        val: signed integer
        n_bits: number of bits (which must reflect a whole number of bytes)

    Returns:
        unsigned integer: two's complement version

    """
    assert n_bits % 8 == 0, "Must specify a whole number of bytes"
    n_bytes = n_bits // 8
    b = val.to_bytes(n_bytes, byteorder=sys.byteorder, signed=True)
    return int.from_bytes(b, byteorder=sys.byteorder, signed=False)


def bytes_to_long(bytesdata: bytes) -> int:
    """
    Converts an 8-byte sequence to a long integer.

    Args:
        bytesdata: 8 consecutive bytes, as a ``bytes`` object, in
            little-endian format (least significant byte [LSB] first)

    Returns:
        integer

    """
    assert len(bytesdata) == 8
    return sum((b << (k * 8) for k, b in enumerate(bytesdata)))


# =============================================================================
# Pure Python implementations of MurmurHash3
# =============================================================================

# -----------------------------------------------------------------------------
# SO ones
# -----------------------------------------------------------------------------


def murmur3_x86_32(data: Union[bytes, bytearray], seed: int = 0) -> int:
    """
    Pure 32-bit Python implementation of MurmurHash3; see
    https://stackoverflow.com/questions/13305290/is-there-a-pure-python-implementation-of-murmurhash.

    Args:
        data: data to hash
        seed: seed

    Returns:
        integer hash

    """  # noqa
    c1 = 0xCC9E2D51
    c2 = 0x1B873593

    length = len(data)
    h1 = seed
    rounded_end = length & 0xFFFFFFFC  # round down to 4 byte block
    for i in range(0, rounded_end, 4):
        # little endian load order
        # RNC: removed ord() calls
        k1 = (
            (data[i] & 0xFF)
            | ((data[i + 1] & 0xFF) << 8)
            | ((data[i + 2] & 0xFF) << 16)
            | (data[i + 3] << 24)
        )
        k1 *= c1
        k1 = (k1 << 15) | ((k1 & 0xFFFFFFFF) >> 17)  # ROTL32(k1, 15)
        k1 *= c2

        h1 ^= k1
        h1 = (h1 << 13) | ((h1 & 0xFFFFFFFF) >> 19)  # ROTL32(h1, 13)
        h1 = h1 * 5 + 0xE6546B64

    # tail
    k1 = 0

    val = length & 0x03
    if val == 3:
        k1 = (data[rounded_end + 2] & 0xFF) << 16
    # fallthrough
    if val in (2, 3):
        k1 |= (data[rounded_end + 1] & 0xFF) << 8
    # fallthrough
    if val in (1, 2, 3):
        k1 |= data[rounded_end] & 0xFF
        k1 *= c1
        k1 = (k1 << 15) | ((k1 & 0xFFFFFFFF) >> 17)  # ROTL32(k1, 15)
        k1 *= c2
        h1 ^= k1

    # finalization
    h1 ^= length

    # fmix(h1)
    h1 ^= (h1 & 0xFFFFFFFF) >> 16
    h1 *= 0x85EBCA6B
    h1 ^= (h1 & 0xFFFFFFFF) >> 13
    h1 *= 0xC2B2AE35
    h1 ^= (h1 & 0xFFFFFFFF) >> 16

    return h1 & 0xFFFFFFFF


# noinspection PyPep8
def murmur3_64(data: Union[bytes, bytearray], seed: int = 19820125) -> int:
    """
    Pure 64-bit Python implementation of MurmurHash3; see
    https://stackoverflow.com/questions/13305290/is-there-a-pure-python-implementation-of-murmurhash
    (plus RNC bugfixes).

    Args:
        data: data to hash
        seed: seed

    Returns:
        integer hash
    """  # noqa
    m = 0xC6A4A7935BD1E995
    r = 47

    mask = 2**64 - 1

    length = len(data)

    h = seed ^ ((m * length) & mask)

    offset = (length // 8) * 8
    # RNC: was /, but for Python 3 that gives float; brackets added for clarity
    for ll in range(0, offset, 8):
        k = bytes_to_long(data[ll : ll + 8])
        k = (k * m) & mask
        k ^= (k >> r) & mask
        k = (k * m) & mask
        h = h ^ k
        h = (h * m) & mask

    # Variable was named "l"; renamed to "l_" for PEP8
    l_ = length & 7

    if l_ >= 7:
        h = h ^ (data[offset + 6] << 48)

    if l_ >= 6:
        h = h ^ (data[offset + 5] << 40)

    if l_ >= 5:
        h = h ^ (data[offset + 4] << 32)

    if l_ >= 4:
        h = h ^ (data[offset + 3] << 24)

    if l_ >= 3:
        h = h ^ (data[offset + 2] << 16)

    if l_ >= 2:
        h = h ^ (data[offset + 1] << 8)

    if l_ >= 1:
        h = h ^ data[offset]
        h = (h * m) & mask

    h ^= (h >> r) & mask
    h = (h * m) & mask
    h ^= (h >> r) & mask

    return h


# -----------------------------------------------------------------------------
# pymmh3 ones, renamed, with some bugfixes
# -----------------------------------------------------------------------------


def pymmh3_hash128_x64(key: Union[bytes, bytearray], seed: int) -> int:
    """
    Implements 128-bit murmur3 hash for x64, as per ``pymmh3``, with some
    bugfixes.

    Args:
        key: data to hash
        seed: seed

    Returns:
        integer hash
    """

    def fmix(k):
        k ^= k >> 33
        k = (k * 0xFF51AFD7ED558CCD) & 0xFFFFFFFFFFFFFFFF
        k ^= k >> 33
        k = (k * 0xC4CEB9FE1A85EC53) & 0xFFFFFFFFFFFFFFFF
        k ^= k >> 33
        return k

    length = len(key)
    nblocks = int(length / 16)

    h1 = seed
    h2 = seed

    c1 = 0x87C37B91114253D5
    c2 = 0x4CF5AD432745937F

    # body
    for block_start in range(0, nblocks * 8, 8):
        # ??? big endian?
        k1 = (
            key[2 * block_start + 7] << 56
            | key[2 * block_start + 6] << 48
            | key[2 * block_start + 5] << 40
            | key[2 * block_start + 4] << 32
            | key[2 * block_start + 3] << 24
            | key[2 * block_start + 2] << 16
            | key[2 * block_start + 1] << 8
            | key[2 * block_start + 0]
        )

        k2 = (
            key[2 * block_start + 15] << 56
            | key[2 * block_start + 14] << 48
            | key[2 * block_start + 13] << 40
            | key[2 * block_start + 12] << 32
            | key[2 * block_start + 11] << 24
            | key[2 * block_start + 10] << 16
            | key[2 * block_start + 9] << 8
            | key[2 * block_start + 8]
        )

        k1 = (c1 * k1) & 0xFFFFFFFFFFFFFFFF
        k1 = (k1 << 31 | k1 >> 33) & 0xFFFFFFFFFFFFFFFF  # inlined ROTL64
        k1 = (c2 * k1) & 0xFFFFFFFFFFFFFFFF
        h1 ^= k1

        h1 = (h1 << 27 | h1 >> 37) & 0xFFFFFFFFFFFFFFFF  # inlined ROTL64
        h1 = (h1 + h2) & 0xFFFFFFFFFFFFFFFF
        h1 = (h1 * 5 + 0x52DCE729) & 0xFFFFFFFFFFFFFFFF

        k2 = (c2 * k2) & 0xFFFFFFFFFFFFFFFF
        k2 = (k2 << 33 | k2 >> 31) & 0xFFFFFFFFFFFFFFFF  # inlined ROTL64
        k2 = (c1 * k2) & 0xFFFFFFFFFFFFFFFF
        h2 ^= k2

        h2 = (h2 << 31 | h2 >> 33) & 0xFFFFFFFFFFFFFFFF  # inlined ROTL64
        h2 = (h1 + h2) & 0xFFFFFFFFFFFFFFFF
        h2 = (h2 * 5 + 0x38495AB5) & 0xFFFFFFFFFFFFFFFF

    # tail
    tail_index = nblocks * 16
    k1 = 0
    k2 = 0
    tail_size = length & 15

    if tail_size >= 15:
        k2 ^= key[tail_index + 14] << 48
    if tail_size >= 14:
        k2 ^= key[tail_index + 13] << 40
    if tail_size >= 13:
        k2 ^= key[tail_index + 12] << 32
    if tail_size >= 12:
        k2 ^= key[tail_index + 11] << 24
    if tail_size >= 11:
        k2 ^= key[tail_index + 10] << 16
    if tail_size >= 10:
        k2 ^= key[tail_index + 9] << 8
    if tail_size >= 9:
        k2 ^= key[tail_index + 8]

    if tail_size > 8:
        k2 = (k2 * c2) & 0xFFFFFFFFFFFFFFFF
        k2 = (k2 << 33 | k2 >> 31) & 0xFFFFFFFFFFFFFFFF  # inlined ROTL64
        k2 = (k2 * c1) & 0xFFFFFFFFFFFFFFFF
        h2 ^= k2

    if tail_size >= 8:
        k1 ^= key[tail_index + 7] << 56
    if tail_size >= 7:
        k1 ^= key[tail_index + 6] << 48
    if tail_size >= 6:
        k1 ^= key[tail_index + 5] << 40
    if tail_size >= 5:
        k1 ^= key[tail_index + 4] << 32
    if tail_size >= 4:
        k1 ^= key[tail_index + 3] << 24
    if tail_size >= 3:
        k1 ^= key[tail_index + 2] << 16
    if tail_size >= 2:
        k1 ^= key[tail_index + 1] << 8
    if tail_size >= 1:
        k1 ^= key[tail_index + 0]

    if tail_size > 0:
        k1 = (k1 * c1) & 0xFFFFFFFFFFFFFFFF
        k1 = (k1 << 31 | k1 >> 33) & 0xFFFFFFFFFFFFFFFF  # inlined ROTL64
        k1 = (k1 * c2) & 0xFFFFFFFFFFFFFFFF
        h1 ^= k1

    # finalization
    h1 ^= length
    h2 ^= length

    h1 = (h1 + h2) & 0xFFFFFFFFFFFFFFFF
    h2 = (h1 + h2) & 0xFFFFFFFFFFFFFFFF

    h1 = fmix(h1)
    h2 = fmix(h2)

    h1 = (h1 + h2) & 0xFFFFFFFFFFFFFFFF
    h2 = (h1 + h2) & 0xFFFFFFFFFFFFFFFF

    return h2 << 64 | h1


def pymmh3_hash128_x86(key: Union[bytes, bytearray], seed: int) -> int:
    """
    Implements 128-bit murmur3 hash for x86, as per ``pymmh3``, with some
    bugfixes.

    Args:
        key: data to hash
        seed: seed

    Returns:
        integer hash
    """

    def fmix(h):
        h ^= h >> 16
        h = (h * 0x85EBCA6B) & 0xFFFFFFFF
        h ^= h >> 13
        h = (h * 0xC2B2AE35) & 0xFFFFFFFF
        h ^= h >> 16
        return h

    length = len(key)
    nblocks = int(length / 16)

    h1 = seed
    h2 = seed
    h3 = seed
    h4 = seed

    c1 = 0x239B961B
    c2 = 0xAB0E9789
    c3 = 0x38B34AE5
    c4 = 0xA1E38B93

    # body
    for block_start in range(0, nblocks * 16, 16):
        k1 = (
            key[block_start + 3] << 24
            | key[block_start + 2] << 16
            | key[block_start + 1] << 8
            | key[block_start + 0]
        )
        k2 = (
            key[block_start + 7] << 24
            | key[block_start + 6] << 16
            | key[block_start + 5] << 8
            | key[block_start + 4]
        )
        k3 = (
            key[block_start + 11] << 24
            | key[block_start + 10] << 16
            | key[block_start + 9] << 8
            | key[block_start + 8]
        )
        k4 = (
            key[block_start + 15] << 24
            | key[block_start + 14] << 16
            | key[block_start + 13] << 8
            | key[block_start + 12]
        )

        k1 = (c1 * k1) & 0xFFFFFFFF
        k1 = (k1 << 15 | k1 >> 17) & 0xFFFFFFFF  # inlined ROTL32
        k1 = (c2 * k1) & 0xFFFFFFFF
        h1 ^= k1

        h1 = (h1 << 19 | h1 >> 13) & 0xFFFFFFFF  # inlined ROTL32
        h1 = (h1 + h2) & 0xFFFFFFFF
        h1 = (h1 * 5 + 0x561CCD1B) & 0xFFFFFFFF

        k2 = (c2 * k2) & 0xFFFFFFFF
        k2 = (k2 << 16 | k2 >> 16) & 0xFFFFFFFF  # inlined ROTL32
        k2 = (c3 * k2) & 0xFFFFFFFF
        h2 ^= k2

        h2 = (h2 << 17 | h2 >> 15) & 0xFFFFFFFF  # inlined ROTL32
        h2 = (h2 + h3) & 0xFFFFFFFF
        h2 = (h2 * 5 + 0x0BCAA747) & 0xFFFFFFFF

        k3 = (c3 * k3) & 0xFFFFFFFF
        k3 = (k3 << 17 | k3 >> 15) & 0xFFFFFFFF  # inlined ROTL32
        k3 = (c4 * k3) & 0xFFFFFFFF
        h3 ^= k3

        h3 = (h3 << 15 | h3 >> 17) & 0xFFFFFFFF  # inlined ROTL32
        h3 = (h3 + h4) & 0xFFFFFFFF
        h3 = (h3 * 5 + 0x96CD1C35) & 0xFFFFFFFF

        k4 = (c4 * k4) & 0xFFFFFFFF
        k4 = (k4 << 18 | k4 >> 14) & 0xFFFFFFFF  # inlined ROTL32
        k4 = (c1 * k4) & 0xFFFFFFFF
        h4 ^= k4

        h4 = (h4 << 13 | h4 >> 19) & 0xFFFFFFFF  # inlined ROTL32
        h4 = (h1 + h4) & 0xFFFFFFFF
        h4 = (h4 * 5 + 0x32AC3B17) & 0xFFFFFFFF

    # tail
    tail_index = nblocks * 16
    k1 = 0
    k2 = 0
    k3 = 0
    k4 = 0
    tail_size = length & 15

    if tail_size >= 15:
        k4 ^= key[tail_index + 14] << 16
    if tail_size >= 14:
        k4 ^= key[tail_index + 13] << 8
    if tail_size >= 13:
        k4 ^= key[tail_index + 12]

    if tail_size > 12:
        k4 = (k4 * c4) & 0xFFFFFFFF
        k4 = (k4 << 18 | k4 >> 14) & 0xFFFFFFFF  # inlined ROTL32
        k4 = (k4 * c1) & 0xFFFFFFFF
        h4 ^= k4

    if tail_size >= 12:
        k3 ^= key[tail_index + 11] << 24
    if tail_size >= 11:
        k3 ^= key[tail_index + 10] << 16
    if tail_size >= 10:
        k3 ^= key[tail_index + 9] << 8
    if tail_size >= 9:
        k3 ^= key[tail_index + 8]

    if tail_size > 8:
        k3 = (k3 * c3) & 0xFFFFFFFF
        k3 = (k3 << 17 | k3 >> 15) & 0xFFFFFFFF  # inlined ROTL32
        k3 = (k3 * c4) & 0xFFFFFFFF
        h3 ^= k3

    if tail_size >= 8:
        k2 ^= key[tail_index + 7] << 24
    if tail_size >= 7:
        k2 ^= key[tail_index + 6] << 16
    if tail_size >= 6:
        k2 ^= key[tail_index + 5] << 8
    if tail_size >= 5:
        k2 ^= key[tail_index + 4]

    if tail_size > 4:
        k2 = (k2 * c2) & 0xFFFFFFFF
        k2 = (k2 << 16 | k2 >> 16) & 0xFFFFFFFF  # inlined ROTL32
        k2 = (k2 * c3) & 0xFFFFFFFF
        h2 ^= k2

    if tail_size >= 4:
        k1 ^= key[tail_index + 3] << 24
    if tail_size >= 3:
        k1 ^= key[tail_index + 2] << 16
    if tail_size >= 2:
        k1 ^= key[tail_index + 1] << 8
    if tail_size >= 1:
        k1 ^= key[tail_index + 0]

    if tail_size > 0:
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = (k1 << 15 | k1 >> 17) & 0xFFFFFFFF  # inlined ROTL32
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1

    # finalization
    h1 ^= length
    h2 ^= length
    h3 ^= length
    h4 ^= length

    h1 = (h1 + h2) & 0xFFFFFFFF
    h1 = (h1 + h3) & 0xFFFFFFFF
    h1 = (h1 + h4) & 0xFFFFFFFF
    h2 = (h1 + h2) & 0xFFFFFFFF
    h3 = (h1 + h3) & 0xFFFFFFFF
    h4 = (h1 + h4) & 0xFFFFFFFF

    h1 = fmix(h1)
    h2 = fmix(h2)
    h3 = fmix(h3)
    h4 = fmix(h4)

    h1 = (h1 + h2) & 0xFFFFFFFF
    h1 = (h1 + h3) & 0xFFFFFFFF
    h1 = (h1 + h4) & 0xFFFFFFFF
    h2 = (h1 + h2) & 0xFFFFFFFF
    h3 = (h1 + h3) & 0xFFFFFFFF
    h4 = (h1 + h4) & 0xFFFFFFFF

    return h4 << 96 | h3 << 64 | h2 << 32 | h1


def pymmh3_hash128(
    key: Union[bytes, bytearray], seed: int = 0, x64arch: bool = True
) -> int:
    """
    Implements 128bit murmur3 hash, as per ``pymmh3``.

    Args:
        key: data to hash
        seed: seed
        x64arch: is a 64-bit architecture available?

    Returns:
        integer hash

    """
    if x64arch:
        return pymmh3_hash128_x64(key, seed)
    else:
        return pymmh3_hash128_x86(key, seed)


def pymmh3_hash64(
    key: Union[bytes, bytearray], seed: int = 0, x64arch: bool = True
) -> Tuple[int, int]:
    """
    Implements 64bit murmur3 hash, as per ``pymmh3``. Returns a tuple.

    Args:
        key: data to hash
        seed: seed
        x64arch: is a 64-bit architecture available?

    Returns:
        tuple: tuple of integers, ``(signed_val1, signed_val2)``

    """

    hash_128 = pymmh3_hash128(key, seed, x64arch)

    unsigned_val1 = hash_128 & 0xFFFFFFFFFFFFFFFF  # low half
    if unsigned_val1 & 0x8000000000000000 == 0:
        signed_val1 = unsigned_val1
    else:
        signed_val1 = -((unsigned_val1 ^ 0xFFFFFFFFFFFFFFFF) + 1)

    unsigned_val2 = (hash_128 >> 64) & 0xFFFFFFFFFFFFFFFF  # high half
    if unsigned_val2 & 0x8000000000000000 == 0:
        signed_val2 = unsigned_val2
    else:
        signed_val2 = -((unsigned_val2 ^ 0xFFFFFFFFFFFFFFFF) + 1)

    return signed_val1, signed_val2


# =============================================================================
# Checks
# =============================================================================


def compare_python_to_reference_murmur3_32(data: Any, seed: int = 0) -> None:
    """
    Checks the pure Python implementation of 32-bit murmur3 against the
    ``mmh3`` C-based module.

    Args:
        data: data to hash
        seed: seed

    Raises:
        AssertionError: if the two calculations don't match

    """
    assert mmh3, "Need mmh3 module"
    c_data = to_str(data)
    # noinspection PyUnresolvedReferences
    c_signed = mmh3.hash(c_data, seed=seed)  # 32 bit
    py_data = to_bytes(c_data)
    py_unsigned = murmur3_x86_32(py_data, seed=seed)
    py_signed = twos_comp_to_signed(py_unsigned, n_bits=32)
    preamble = f"Hashing {data!r} with MurmurHash3/32-bit/seed={seed}"
    if c_signed == py_signed:
        print(preamble + f" -> {c_signed}: OK")
    else:
        raise AssertionError(
            preamble + f"; mmh3 says {c_data!r} -> {c_signed}, "
            f"Python version says {py_data!r} -> {py_unsigned} = {py_signed}"
        )


def compare_python_to_reference_murmur3_64(data: Any, seed: int = 0) -> None:
    """
    Checks the pure Python implementation of 64-bit murmur3 against the
    ``mmh3`` C-based module.

    Args:
        data: data to hash
        seed: seed

    Raises:
        AssertionError: if the two calculations don't match

    """
    assert mmh3, "Need mmh3 module"
    c_data = to_str(data)
    # noinspection PyUnresolvedReferences
    c_signed_low, c_signed_high = mmh3.hash64(
        c_data, seed=seed, x64arch=IS_64_BIT
    )
    py_data = to_bytes(c_data)
    py_signed_low, py_signed_high = pymmh3_hash64(py_data, seed=seed)
    preamble = (
        f"Hashing {data!r} with MurmurHash3/64-bit values from 128-bit "
        f"hash/seed={seed}"
    )
    if c_signed_low == py_signed_low and c_signed_high == py_signed_high:
        print(preamble + f" -> (low={c_signed_low}, high={c_signed_high}): OK")
    else:
        raise AssertionError(
            preamble + f"; mmh3 says {c_data!r} -> "
            f"(low={c_signed_low}, high={c_signed_high}), "
            f"Python version says {py_data!r} -> "
            f"(low={py_signed_low}, high={py_signed_high})"
        )


# =============================================================================
# Hashing in a NON-CRYPTOGRAPHIC, PREDICTABLE, and fast way
# =============================================================================


def hash32(data: Any, seed: int = 0) -> int:
    """
    Non-cryptographic, deterministic, fast hash.

    Args:
        data: data to hash
        seed: seed

    Returns:
        signed 32-bit integer
    """
    c_data = to_str(data)
    if mmh3:
        # noinspection PyUnresolvedReferences
        return mmh3.hash(c_data, seed=seed)
    py_data = to_bytes(c_data)
    py_unsigned = murmur3_x86_32(py_data, seed=seed)
    return twos_comp_to_signed(py_unsigned, n_bits=32)


def hash64(data: Any, seed: int = 0) -> int:
    """
    Non-cryptographic, deterministic, fast hash.

    Args:
        data: data to hash
        seed: seed

    Returns:
        signed 64-bit integer
    """
    # -------------------------------------------------------------------------
    # MurmurHash3
    # -------------------------------------------------------------------------
    c_data = to_str(data)
    if mmh3:
        # noinspection PyUnresolvedReferences
        c_signed_low, _ = mmh3.hash64(data, seed=seed, x64arch=IS_64_BIT)
        return c_signed_low
    py_data = to_bytes(c_data)
    py_signed_low, _ = pymmh3_hash64(py_data, seed=seed)
    return py_signed_low

    # -------------------------------------------------------------------------
    # xxHash
    # -------------------------------------------------------------------------
    # if xxhash:
    #     hasher = xxhash.xxh64(seed=0)
    #     hasher.update(data)
    #     return hasher.intdigest()
    # else:
    #     hasher = pyhashxx.Hashxx(seed=0)
    #     # then do some update, but it doesn't like plain strings...
    #     return hasher.digest()


# =============================================================================
# Testing
# =============================================================================


def main() -> None:
    """
    Command-line validation checks.
    """
    _ = """
    print(twos_comp_to_signed(0, n_bits=32))  # 0
    print(twos_comp_to_signed(2 ** 31 - 1, n_bits=32))  # 2147483647
    print(twos_comp_to_signed(2 ** 31, n_bits=32))  # -2147483648 == -(2 ** 31)
    print(twos_comp_to_signed(2 ** 32 - 1, n_bits=32))  # -1
    print(signed_to_twos_comp(-1, n_bits=32))  # 4294967295 = 2 ** 32 - 1
    print(signed_to_twos_comp(-(2 ** 31), n_bits=32))  # 2147483648 = 2 ** 31 - 1
    """  # noqa
    testdata = ["hello", 1, ["bongos", "today"]]
    for data in testdata:
        compare_python_to_reference_murmur3_32(data, seed=0)
        compare_python_to_reference_murmur3_64(data, seed=0)
    print("All OK")


if __name__ == "__main__":
    main()
