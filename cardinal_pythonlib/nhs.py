#!/usr/bin/env python
# cardinal_pythonlib/nhs.py

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

**Support functions regarding NHS numbers, etc.**

"""

import re
import logging
import random
from typing import List, Optional, Union

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# NHS number validation
# =============================================================================

NHS_DIGIT_WEIGHTINGS = [10, 9, 8, 7, 6, 5, 4, 3, 2]


def nhs_check_digit(ninedigits: Union[str, List[Union[str, int]]]) -> int:
    """
    Calculates an NHS number check digit.

    Args:
        ninedigits: string or list

    Returns:
        check digit

    Method:

    1. Multiply each of the first nine digits by the corresponding
       digit weighting (see :const:`NHS_DIGIT_WEIGHTINGS`).
    2. Sum the results.
    3. Take remainder after division by 11.
    4. Subtract the remainder from 11
    5. If this is 11, use 0 instead
       If it's 10, the number is invalid
       If it doesn't match the actual check digit, the number is invalid

    """
    if len(ninedigits) != 9 or not all(str(x).isdigit() for x in ninedigits):
        raise ValueError("bad string to nhs_check_digit")
    check_digit = 11 - (sum([
        int(d) * f
        for (d, f) in zip(ninedigits, NHS_DIGIT_WEIGHTINGS)
    ]) % 11)
    # ... % 11 yields something in the range 0-10
    # ... 11 - that yields something in the range 1-11
    if check_digit == 11:
        check_digit = 0
    return check_digit


def is_valid_nhs_number(n: int) -> bool:
    """
    Validates an integer as an NHS number.
    
    Args:
        n: NHS number

    Returns:
        valid?

    Checksum details are at
    http://www.datadictionary.nhs.uk/version2/data_dictionary/data_field_notes/n/nhs_number_de.asp
    """  # noqa
    if not isinstance(n, int):
        log.debug("is_valid_nhs_number: parameter was not of integer type")
        return False

    s = str(n)
    # Not 10 digits long?
    if len(s) != 10:
        log.debug("is_valid_nhs_number: not 10 digits")
        return False

    main_digits = [int(s[i]) for i in range(9)]
    actual_check_digit = int(s[9])  # tenth digit
    expected_check_digit = nhs_check_digit(main_digits)
    if expected_check_digit == 10:
        log.debug("is_valid_nhs_number: calculated check digit invalid")
        return False
    if expected_check_digit != actual_check_digit:
        log.debug("is_valid_nhs_number: check digit mismatch")
        return False
    # Hooray!
    return True


def generate_random_nhs_number() -> int:
    """
    Returns a random valid NHS number, as an ``int``.
    """
    check_digit = 10  # NHS numbers with this check digit are all invalid
    while check_digit == 10:
        digits = [random.randint(1, 9)]  # don't start with a zero
        digits.extend([random.randint(0, 9) for _ in range(8)])
        # ... length now 9
        check_digit = nhs_check_digit(digits)
    # noinspection PyUnboundLocalVariable
    digits.append(check_digit)
    return int("".join([str(d) for d in digits]))


def test_nhs_rng(n: int = 100) -> None:
    """Tests the NHS random number generator."""
    for i in range(n):
        x = generate_random_nhs_number()
        assert is_valid_nhs_number(x), "Invalid NHS number: {}".format(x)


def generate_nhs_number_from_first_9_digits(first9digits: str) -> Optional[int]:
    """
    Returns a valid NHS number, as an ``int``, given the first 9 digits.
    The particular purpose is to make NHS numbers that *look* fake (rather
    than truly random NHS numbers which might accidentally be real).

    For example:

    .. code-block:: none

        123456789_ : no; checksum 10
        987654321_ : yes, valid if completed to 9876543210
        999999999_ : yes, valid if completed to 9999999999
    """
    if len(first9digits) != 9:
        log.warning("Not 9 digits")
        return None
    try:
        first9int = int(first9digits)
    except (TypeError, ValueError):
        log.warning("Not an integer")
        return None  # not an int
    if len(str(first9int)) != len(first9digits):
        # e.g. leading zeros, or some such
        log.warning("Leading zeros?")
        return None
    check_digit = nhs_check_digit(first9digits)
    if check_digit == 10:  # NHS numbers with this check digit are all invalid
        log.warning("Can't have check digit of 10")
        return None
    return int(first9digits + str(check_digit))


# =============================================================================
# Get an NHS number out of text
# =============================================================================

WHITESPACE_REGEX = re.compile('\s')
NON_NUMERIC_REGEX = re.compile("[^0-9]")  # or "\D"


def nhs_number_from_text_or_none(s: str) -> Optional[int]:
    """
    Returns a validated NHS number (as an integer) from a string, or ``None``
    if it is not valid.
    
    It's a 10-digit number, so note that database 32-bit INT values are
    insufficient; use BIGINT. Python will handle large integers happily.
    
    NHS number rules:        
    http://www.datadictionary.nhs.uk/version2/data_dictionary/data_field_notes/n/nhs_number_de.asp?shownav=0
    """  # noqa
    # None in, None out.
    funcname = "nhs_number_from_text_or_none: "
    if not s:
        log.debug(funcname + "incoming parameter was None")
        return None

    # (a) If it's not a 10-digit number, bye-bye.

    # Remove whitespace
    s = WHITESPACE_REGEX.sub("", s)  # replaces all instances
    # Contains non-numeric characters?
    if NON_NUMERIC_REGEX.search(s):
        log.debug(funcname + "contains non-numeric characters")
        return None
    # Not 10 digits long?
    if len(s) != 10:
        log.debug(funcname + "not 10 digits long")
        return None

    # (b) Validation
    n = int(s)
    if not is_valid_nhs_number(n):
        log.debug(funcname + "failed validation")
        return None

    # Happy!
    return n
