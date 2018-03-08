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
from string import Formatter
from typing import Any, Optional, Union

try:
    from arrow import Arrow
except ImportError:
    Arrow = None
try:
    import dateutil.parser
except ImportError:
    dateutil = None
import pendulum
from pendulum import Date, Pendulum, Time
import tzlocal

PotentialDatetimeType = Union[None, datetime.datetime, datetime.date,
                              Pendulum, str, Arrow]
DateTimeLikeType = Union[datetime.datetime, Pendulum, Arrow]
DateLikeType = Union[datetime.date, Pendulum, Arrow]


# =============================================================================
# Coerce things to our favourite datetime class
# ... including adding timezone information to timezone-naive objects
# =============================================================================

def coerce_to_pendulum(x: PotentialDatetimeType,
                       assume_local: bool = False) -> Optional[Pendulum]:
    """
    Converts something to a Pendulum, or None.
    May raise:
        pendulum.parsing.exceptions.ParserError
        ValueError
    """
    if not x:  # None and blank string
        return None
    if isinstance(x, Pendulum):
        return x
    tz = get_tz_local() if assume_local else get_tz_utc()
    if isinstance(x, datetime.datetime):
        return pendulum.instance(x, tz=tz)  # (*)
    elif isinstance(x, datetime.date):
        # BEWARE: datetime subclasses date. The order is crucial here.
        # Can also use: type(x) is datetime.date
        # noinspection PyUnresolvedReferences
        midnight = Pendulum.min.time()
        dt = Pendulum.combine(x, midnight)
        return pendulum.instance(dt, tz=tz)  # (*)
    elif isinstance(x, str):
        return pendulum.parse(x, tz=tz)  # (*)  # may raise
    else:
        raise ValueError("Don't know how to convert to Pendulum: "
                         "{!r}".format(x))
    # (*) If x already knew its timezone, it will not
    # be altered; "tz" will only be applied in the absence of other info.


def coerce_to_pendulum_date(x: PotentialDatetimeType,
                            assume_local: bool = False) -> Optional[Date]:
    p = coerce_to_pendulum(x, assume_local=assume_local)
    if p is None:
        return None
    return p.date()


def pendulum_to_datetime(x: Pendulum) -> datetime.datetime:
    """
    Used, for example, where a database backend insists on datetime.datetime.
    """
    # noinspection PyProtectedMember
    return x._datetime


def pendulum_date_to_datetime_date(x: Date) -> datetime.date:
    """
    Used, for example, where a database backend insists on datetime.date.
    """
    return datetime.date(year=x.year, month=x.month, day=x.day)


def pendulum_time_to_datetime_time(x: Time) -> datetime.time:
    """
    Used, for example, where a database backend insists on datetime.time.
    """
    # noinspection PyProtectedMember
    return x._time


# =============================================================================
# Format dates/times/timedelta to strings
# =============================================================================

def format_datetime(d: PotentialDatetimeType,
                    fmt: str,
                    default: str = None) -> Optional[str]:
    """Format a datetime with a format string, or return default if None."""
    d = coerce_to_pendulum(d)
    if d is None:
        return default
    return d.strftime(fmt)


def strfdelta(tdelta: Union[datetime.timedelta, int, float, str],
              fmt='{D:02}d {H:02}h {M:02}m {S:02}s',
              inputtype='timedelta'):
    # Modified from:
    # https://stackoverflow.com/questions/538666/python-format-timedelta-to-string  # noqa
    """
    Convert a datetime.timedelta object or a regular number to a custom-
    formatted string, just like the strftime() method does for
    datetime.datetime objects.

    The fmt argument allows custom formatting to be specified.  Fields can
    include seconds, minutes, hours, days, and weeks.  Each field is optional.

    Some examples:
        '{D:02}d {H:02}h {M:02}m {S:02}s' --> '05d 08h 04m 02s' (default)
        '{W}w {D}d {H}:{M:02}:{S:02}'     --> '4w 5d 8:04:02'
        '{D:2}d {H:2}:{M:02}:{S:02}'      --> ' 5d  8:04:02'
        '{H}h {S}s'                       --> '72h 800s'

    The inputtype argument allows tdelta to be a regular number instead of the
    default, which is a datetime.timedelta object.  Valid inputtype strings:
        's', 'seconds',
        'm', 'minutes',
        'h', 'hours',
        'd', 'days',
        'w', 'weeks'
    """

    # Convert tdelta to integer seconds.
    if inputtype == 'timedelta':
        remainder = int(tdelta.total_seconds())
    elif inputtype in ['s', 'seconds']:
        remainder = int(tdelta)
    elif inputtype in ['m', 'minutes']:
        remainder = int(tdelta) * 60
    elif inputtype in ['h', 'hours']:
        remainder = int(tdelta) * 3600
    elif inputtype in ['d', 'days']:
        remainder = int(tdelta) * 86400
    elif inputtype in ['w', 'weeks']:
        remainder = int(tdelta) * 604800
    else:
        raise ValueError("Bad inputtype: {}".format(inputtype))

    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ('W', 'D', 'H', 'M', 'S')
    constants = {'W': 604800, 'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    values = {}
    for field in possible_fields:
        if field in desired_fields and field in constants:
            values[field], remainder = divmod(remainder, constants[field])
    return f.format(fmt, **values)


# =============================================================================
# Time zones themselves
# =============================================================================

def get_tz_local() -> datetime.tzinfo:
    return tzlocal.get_localzone()


def get_tz_utc() -> datetime.tzinfo:
    return pendulum.UTC


# =============================================================================
# Now
# =============================================================================

def get_now_localtz_pendulum() -> Pendulum:
    """Get the time now in the local timezone."""
    tz = get_tz_local()
    return pendulum.now().in_tz(tz)


def get_now_utc_pendulum() -> Pendulum:
    """Get the time now in the UTC timezone."""
    tz = get_tz_utc()
    return pendulum.utcnow().in_tz(tz)


def get_now_utc_datetime() -> datetime.datetime:
    """Get the time now in the UTC timezone."""
    return datetime.datetime.now(pendulum.UTC)


# =============================================================================
# From one timezone to another
# =============================================================================

def convert_datetime_to_utc(dt: PotentialDatetimeType) -> Pendulum:
    """Convert date/time with timezone to UTC (with UTC timezone)."""
    dt = coerce_to_pendulum(dt)
    tz = get_tz_utc()
    return dt.in_tz(tz)


def convert_datetime_to_local(dt: PotentialDatetimeType) -> Pendulum:
    """Convert date/time with timezone to local timezone."""
    dt = coerce_to_pendulum(dt)
    tz = get_tz_local()
    return dt.in_tz(tz)


# =============================================================================
# Time differences
# =============================================================================

def get_duration_h_m(start: Union[str, Pendulum],
                     end: Union[str, Pendulum],
                     default: str = "N/A") -> str:
    """Calculate the time between two dates/times expressed as strings.

    Return format: string, as one of:
        hh:mm
        -hh:mm
    or
        default parameter
    """
    start = coerce_to_pendulum(start)
    end = coerce_to_pendulum(end)
    if start is None or end is None:
        return default
    duration = end - start
    minutes = duration.in_minutes()
    (hours, minutes) = divmod(minutes, 60)
    if hours < 0:
        # negative... trickier
        # Python's divmod does interesting things with negative numbers:
        # Hours will be negative, and minutes always positive
        hours += 1
        minutes = 60 - minutes
        return "-{}:{}".format(hours, "00" if minutes == 0 else minutes)
    else:
        return "{}:{}".format(hours, "00" if minutes == 0 else minutes)


def get_age(dob: PotentialDatetimeType,
            when: PotentialDatetimeType,
            default: str = "") -> Union[int, str]:
    """
    Age (in whole years) at a particular date, or default.
    """
    dob = coerce_to_pendulum(dob)
    when = coerce_to_pendulum(when)
    if dob is None or when is None:
        return default
    return (when - dob).years


# =============================================================================
# Other manipulations
# =============================================================================

def truncate_date_to_first_of_month(
        dt: Optional[DateLikeType]) -> Optional[DateLikeType]:
    """Change the day to the first of the month."""
    if dt is None:
        return None
    return dt.replace(day=1)


# =============================================================================
# Older date/time functions for native Python datetime objects
# =============================================================================

def get_now_utc_notz_datetime() -> datetime.datetime:
    """Get the UTC time now, but with no timezone information."""
    now = datetime.datetime.utcnow()
    return now.replace(tzinfo=None)


def coerce_to_datetime(x: Any) -> Optional[datetime.datetime]:
    """
    Ensure an object is a datetime, or coerce to one, or raise (ValueError or
    OverflowError, as per
    http://dateutil.readthedocs.org/en/latest/parser.html).
    """
    if x is None:
        return None
    elif isinstance(x, Pendulum):
        # noinspection PyProtectedMember
        return x._datetime
    elif isinstance(x, datetime.datetime):
        return x
    elif isinstance(x, datetime.date):
        return datetime.datetime(x.year, x.month, x.day)
    else:
        return dateutil.parser.parse(x)  # may raise
