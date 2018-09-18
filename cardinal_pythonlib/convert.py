#!/usr/bin/env python
# cardinal_pythonlib/convert.py

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

**Miscellaneous other conversions.**

"""

import base64
import binascii
import logging
import re
from typing import Any, Iterable, Optional

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Simple type converters
# =============================================================================

def convert_to_bool(x: Any, default: bool = None) -> bool:
    """
    Transforms its input to a ``bool`` (or returns ``default`` if ``x`` is
    falsy but not itself a boolean). Accepts various common string versions.
    """
    if isinstance(x, bool):
        return x

    if not x:  # None, zero, blank string...
        return default

    try:
        return int(x) != 0
    except (TypeError, ValueError):
        pass

    try:
        return float(x) != 0
    except (TypeError, ValueError):
        pass

    if not isinstance(x, str):
        raise Exception("Unknown thing being converted to bool: {!r}".format(x))

    x = x.upper()
    if x in ["Y", "YES", "T", "TRUE"]:
        return True
    if x in ["N", "NO", "F", "FALSE"]:
        return False

    raise Exception("Unknown thing being converted to bool: {!r}".format(x))


def convert_to_int(x: Any, default: int = None) -> int:
    """
    Transforms its input into an integer, or returns ``default``.
    """
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


# =============================================================================
# Attribute converters
# =============================================================================

def convert_attrs_to_bool(obj: Any,
                          attrs: Iterable[str],
                          default: bool = None) -> None:
    """
    Applies :func:`convert_to_bool` to the specified attributes of an object,
    modifying it in place.
    """
    for a in attrs:
        setattr(obj, a, convert_to_bool(getattr(obj, a), default=default))


def convert_attrs_to_uppercase(obj: Any, attrs: Iterable[str]) -> None:
    """
    Converts the specified attributes of an object to upper case, modifying
    the object in place.
    """
    for a in attrs:
        value = getattr(obj, a)
        if value is None:
            continue
        setattr(obj, a, value.upper())


def convert_attrs_to_lowercase(obj: Any, attrs: Iterable[str]) -> None:
    """
    Converts the specified attributes of an object to lower case, modifying
    the object in place.
    """
    for a in attrs:
        value = getattr(obj, a)
        if value is None:
            continue
        setattr(obj, a, value.lower())


def convert_attrs_to_int(obj: Any,
                         attrs: Iterable[str],
                         default: int = None) -> None:
    """
    Applies :func:`convert_to_int` to the specified attributes of an object,
    modifying it in place.
    """
    for a in attrs:
        value = convert_to_int(getattr(obj, a), default=default)
        setattr(obj, a, value)


# =============================================================================
# Encoding: binary as hex in X'...' format
# =============================================================================

REGEX_HEX_XFORMAT = re.compile("""
    ^X'                             # begins with X'
    ([a-fA-F0-9][a-fA-F0-9])+       # one or more hex pairs
    '$                              # ends with '
    """, re.X)  # re.X allows whitespace/comments in regex
REGEX_BASE64_64FORMAT = re.compile("""
    ^64'                                # begins with 64'
    (?: [A-Za-z0-9+/]{4} )*             # zero or more quads, followed by...
    (?:
        [A-Za-z0-9+/]{2} [AEIMQUYcgkosw048] =       # a triple then an =
     |                                              # or
        [A-Za-z0-9+/] [AQgw] ==                     # a pair then ==
    )?
    '$                                  # ends with '
    """, re.X)  # re.X allows whitespace/comments in regex


def hex_xformat_encode(v: bytes) -> str:
    """
    Encode its input in ``X'{hex}'`` format.

    Example:

    .. code-block:: python

        special_hex_encode(b"hello") == "X'68656c6c6f'"
    """
    return "X'{}'".format(binascii.hexlify(v).decode("ascii"))


def hex_xformat_decode(s: str) -> Optional[bytes]:
    """
    Reverse :func:`hex_xformat_encode`.

    The parameter is a hex-encoded BLOB like

    .. code-block:: none

        "X'CDE7A24B1A9DBA3148BCB7A0B9DA5BB6A424486C'"

    Original purpose and notes:

    - SPECIAL HANDLING for BLOBs: a string like ``X'01FF'`` means a hex-encoded
      BLOB. Titanium is rubbish at BLOBs, so we encode them as special string
      literals.
    - SQLite uses this notation: https://sqlite.org/lang_expr.html
    - Strip off the start and end and convert it to a byte array:
      http://stackoverflow.com/questions/5649407
    """
    if len(s) < 3 or not s.startswith("X'") or not s.endswith("'"):
        return None
    return binascii.unhexlify(s[2:-1])


# =============================================================================
# Encoding: binary as hex in 64'...' format (which is idiosyncratic!)
# =============================================================================

def base64_64format_encode(v: bytes) -> str:
    """
    Encode in ``64'{base64encoded}'`` format.

    Example:

    .. code-block:: python

        base64_64format_encode(b"hello") == "64'aGVsbG8='"
    """
    return "64'{}'".format(base64.b64encode(v).decode('ascii'))


def base64_64format_decode(s: str) -> Optional[bytes]:
    """
    Reverse :func:`base64_64format_encode`.

    Original purpose and notes:

    - THIS IS ANOTHER WAY OF DOING BLOBS: base64 encoding, e.g. a string like
      ``64'cGxlYXN1cmUu'`` is a base-64-encoded BLOB (the ``64'...'`` bit is my
      representation).
    - regex from http://stackoverflow.com/questions/475074
    - better one from http://www.perlmonks.org/?node_id=775820

    """
    if len(s) < 4 or not s.startswith("64'") or not s.endswith("'"):
        return None
    return base64.b64decode(s[3:-1])
