#!/usr/bin/env python
# cardinal_pythonlib/bulk_email/constants.py

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

Constants for the simple bulk e-mail tool.

"""

DB_URL_ENVVAR = "CARDINAL_PYTHONLIB_BULK_EMAIL_DB_URL"

CONTENT_TYPE_MAX_LENGTH = 255
# Can be quite long; see cardinal_pythonlib.httpconst.MimeType
# 255 is the formal limit:
# https://stackoverflow.com/questions/643690/maximum-mimetype-length-when-storing-type-in-db  # noqa

DEFAULT_TIME_BETWEEN_EMAILS_S = 0.5

ENCODING_NAME_MAX_LENGTH = 20  # a guess!
# https://en.wikipedia.org/wiki/Character_encoding

FERNET_KEY_BASE64_LENGTH = 44
# The cryptography.Fernet key is 32 bytes, encrypted via base 64.
# Base 64 encoding: produces 4n/3 characters, so 4 * 32 / 3 = 42.67
# ... padded to multiples of 4, giving 44.

HOSTNAME_MAX_LENGTH = 255

PASSWORD_MAX_LENGTH = 255
PASSWORD_OBSCURING_STRING = "*" * 8

RFC_2822_DATETIME_MAX_LENGTH = 40  # approximately!
# https://datatracker.ietf.org/doc/html/rfc2822#section-3.3
# e.g.
# Wed, 31 Sep 2000 11:29:05 +01:00 (CET)
# 0123456789012345678901234567890123456789
#           1         2         3

USERNAME_MAX_LENGTH = 255
