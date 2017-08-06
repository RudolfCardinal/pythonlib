#!/usr/bin/env python
# cardinal_pythonlib/datetimefunc.py

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

Support functions for date/time.
"""

import datetime
from typing import Any, Optional, Union

from arrow import Arrow
import dateutil.parser
import pytz  # pip install pytz

DATE_LIKE_TYPE = Union[datetime.datetime, datetime.date, Arrow]
DATETIME_LIKE_TYPE = Union[datetime.datetime, Arrow]


# =============================================================================
# Date/time functions
# =============================================================================

def format_datetime(d: DATETIME_LIKE_TYPE,
                    fmt: str,
                    default: str = None) -> str:
    """Format a datetime with a format string, or return default if None."""
    if d is None:
        return default
    return d.strftime(fmt)


def get_now_utc() -> datetime.datetime:
    """Get the time now in the UTC timezone."""
    return datetime.datetime.now(pytz.utc)


def get_now_utc_notz() -> datetime.datetime:
    """Get the UTC time now, but with no timezone information."""
    return get_now_utc().replace(tzinfo=None)


def truncate_date_to_first_of_month(
        dt: Optional[DATE_LIKE_TYPE]) -> Optional[DATE_LIKE_TYPE]:
    """Change the day to the first of the month."""
    if dt is None:
        return None
    return dt.replace(day=1)


def coerce_to_datetime(x: Any) -> Optional[datetime.datetime]:
    """
    Ensure an object is a datetime, or coerce to one, or raise (ValueError or
    OverflowError, as per
    http://dateutil.readthedocs.org/en/latest/parser.html).
    """
    if x is None:
        return None
    elif isinstance(x, datetime.datetime):
        return x
    elif isinstance(x, datetime.date):
        return datetime.datetime(x.year, x.month, x.day)
    else:
        return dateutil.parser.parse(x)  # may raise
