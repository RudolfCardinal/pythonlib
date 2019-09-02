#!/usr/bin/env python
# cardinal_pythonlib/datetimefunc.py

"""
===============================================================================

    Original code copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).

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

**Support functions for date/time.**
"""

import datetime
import logging
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

from isodate.isoduration import parse_duration, Duration as IsodateDuration
# from isodate.isoerror import ISO8601Error
import pendulum
from pendulum import Date, DateTime, Duration, Time
from pendulum.tz import local_timezone
from pendulum.tz.timezone import Timezone
# import tzlocal

PotentialDatetimeType = Union[None, datetime.datetime, datetime.date,
                              DateTime, str, Arrow]
DateTimeLikeType = Union[datetime.datetime, DateTime, Arrow]
DateLikeType = Union[datetime.date, DateTime, Arrow]

log = logging.getLogger(__name__)


# =============================================================================
# Coerce things to our favourite datetime class
# ... including adding timezone information to timezone-naive objects
# =============================================================================

def coerce_to_pendulum(x: PotentialDatetimeType,
                       assume_local: bool = False) -> Optional[DateTime]:
    """
    Converts something to a :class:`pendulum.DateTime`.

    Args:
        x: something that may be coercible to a datetime
        assume_local: if ``True``, assume local timezone; if ``False``, assume
            UTC

    Returns:
        a :class:`pendulum.DateTime`, or ``None``.

    Raises:
        pendulum.parsing.exceptions.ParserError: if a string fails to parse
        ValueError: if no conversion possible
    """
    if not x:  # None and blank string
        return None
    if isinstance(x, DateTime):
        return x
    tz = get_tz_local() if assume_local else get_tz_utc()
    if isinstance(x, datetime.datetime):
        # noinspection PyTypeChecker
        return pendulum.instance(x, tz=tz)  # (*)
    elif isinstance(x, datetime.date):
        # BEWARE: datetime subclasses date. The order is crucial here.
        # Can also use: type(x) is datetime.date
        # noinspection PyUnresolvedReferences
        midnight = DateTime.min.time()
        dt = DateTime.combine(x, midnight)
        # noinspection PyTypeChecker
        return pendulum.instance(dt, tz=tz)  # (*)
    elif isinstance(x, str):
        return pendulum.parse(x, tz=tz)  # (*)  # may raise
    else:
        raise ValueError("Don't know how to convert to DateTime: "
                         "{!r}".format(x))
    # (*) If x already knew its timezone, it will not
    # be altered; "tz" will only be applied in the absence of other info.


def coerce_to_pendulum_date(x: PotentialDatetimeType,
                            assume_local: bool = False) -> Optional[Date]:
    """
    Converts something to a :class:`pendulum.Date`.

    Args:
        x: something that may be coercible to a date
        assume_local: if ``True``, assume local timezone; if ``False``, assume
            UTC

    Returns:
        a :class:`pendulum.Date`, or ``None``.

    Raises:
        pendulum.parsing.exceptions.ParserError: if a string fails to parse
        ValueError: if no conversion possible
    """
    p = coerce_to_pendulum(x, assume_local=assume_local)
    return None if p is None else p.date()


def pendulum_to_datetime(x: DateTime) -> datetime.datetime:
    """
    Used, for example, where a database backend insists on datetime.datetime.

    Compare code in :meth:`pendulum.datetime.DateTime.int_timestamp`.
    """
    return datetime.datetime(
        x.year, x.month, x.day,
        x.hour, x.minute, x.second, x.microsecond,
        tzinfo=x.tzinfo
    )


def pendulum_to_datetime_stripping_tz(x: DateTime) -> datetime.datetime:
    """
    Converts a Pendulum ``DateTime`` to a ``datetime.datetime`` that has had
    timezone information stripped.
    """
    return datetime.datetime(
        x.year, x.month, x.day,
        x.hour, x.minute, x.second, x.microsecond,
        tzinfo=None
    )


def pendulum_to_utc_datetime_without_tz(x: DateTime) -> datetime.datetime:
    """
    Converts a Pendulum ``DateTime`` (which will have timezone information) to
    a ``datetime.datetime`` that (a) has no timezone information, and (b) is
    in UTC.

    Example:

    .. code-block:: python

        import pendulum
        from cardinal_pythonlib.datetimefunc import *
        in_moscow = pendulum.parse("2018-01-01T09:00+0300")  # 9am in Moscow
        in_london = pendulum.UTC.convert(in_moscow)  # 6am in UTC
        dt_utc_from_moscow = pendulum_to_utc_datetime_without_tz(in_moscow)  # 6am, no timezone info
        dt_utc_from_london = pendulum_to_utc_datetime_without_tz(in_london)  # 6am, no timezone info

    """  # noqa
    pendulum_in_utc = pendulum.UTC.convert(x)
    return pendulum_to_datetime_stripping_tz(pendulum_in_utc)


def pendulum_date_to_datetime_date(x: Date) -> datetime.date:
    """
    Takes a :class:`pendulum.Date` and returns a :class:`datetime.date`.
    Used, for example, where a database backend insists on
    :class:`datetime.date`.
    """
    return datetime.date(year=x.year, month=x.month, day=x.day)


def pendulum_time_to_datetime_time(x: Time) -> datetime.time:
    """
    Takes a :class:`pendulum.Time` and returns a :class:`datetime.time`.
    Used, for example, where a database backend insists on
    :class:`datetime.time`.
    """
    return datetime.time(
        hour=x.hour, minute=x.minute, second=x.second,
        microsecond=x.microsecond,
        tzinfo=x.tzinfo
    )


# =============================================================================
# Format dates/times/timedelta to strings
# =============================================================================

def format_datetime(d: PotentialDatetimeType,
                    fmt: str,
                    default: str = None) -> Optional[str]:
    """
    Format a datetime with a ``strftime`` format specification string, or
    return ``default`` if the input is ``None``.
    """
    d = coerce_to_pendulum(d)
    if d is None:
        return default
    return d.strftime(fmt)


def strfdelta(tdelta: Union[datetime.timedelta, int, float, str],
              fmt='{D:02}d {H:02}h {M:02}m {S:02}s',
              inputtype='timedelta'):
    """
    Convert a ``datetime.timedelta`` object or a regular number to a custom-
    formatted string, just like the ``strftime()`` method does for
    ``datetime.datetime`` objects.

    The ``fmt`` argument allows custom formatting to be specified. Fields can
    include ``seconds``, ``minutes``, ``hours``, ``days``, and ``weeks``. Each
    field is optional.

    Some examples:

    .. code-block:: none

        '{D:02}d {H:02}h {M:02}m {S:02}s' --> '05d 08h 04m 02s' (default)
        '{W}w {D}d {H}:{M:02}:{S:02}'     --> '4w 5d 8:04:02'
        '{D:2}d {H:2}:{M:02}:{S:02}'      --> ' 5d  8:04:02'
        '{H}h {S}s'                       --> '72h 800s'

    The ``inputtype`` argument allows ``tdelta`` to be a regular number,
    instead of the default behaviour of treating it as a ``datetime.timedelta``
    object.  Valid ``inputtype`` strings:

    .. code-block:: none

        'timedelta',        # treats input as a datetime.timedelta
        's', 'seconds',
        'm', 'minutes',
        'h', 'hours',
        'd', 'days',
        'w', 'weeks'

    Modified from
    https://stackoverflow.com/questions/538666/python-format-timedelta-to-string
    """  # noqa

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

def get_tz_local() -> Timezone:  # datetime.tzinfo:
    """
    Returns the local timezone, in :class:`pendulum.Timezone`` format.
    (This is a subclass of :class:`datetime.tzinfo`.)
    """
    # return tzlocal.get_localzone()
    return local_timezone()


def get_tz_utc() -> Timezone:  # datetime.tzinfo:
    """
    Returns the UTC timezone.
    """
    return pendulum.UTC


# =============================================================================
# Now
# =============================================================================

def get_now_localtz_pendulum() -> DateTime:
    """
    Get the time now in the local timezone, as a :class:`pendulum.DateTime`.
    """
    tz = get_tz_local()
    return pendulum.now().in_tz(tz)


def get_now_utc_pendulum() -> DateTime:
    """
    Get the time now in the UTC timezone, as a :class:`pendulum.DateTime`.
    """
    tz = get_tz_utc()
    return DateTime.utcnow().in_tz(tz)


def get_now_utc_datetime() -> datetime.datetime:
    """
    Get the time now in the UTC timezone, as a :class:`datetime.datetime`.
    """
    return datetime.datetime.now(pendulum.UTC)


# =============================================================================
# From one timezone to another
# =============================================================================

def convert_datetime_to_utc(dt: PotentialDatetimeType) -> DateTime:
    """
    Convert date/time with timezone to UTC (with UTC timezone).
    """
    dt = coerce_to_pendulum(dt)
    tz = get_tz_utc()
    return dt.in_tz(tz)


def convert_datetime_to_local(dt: PotentialDatetimeType) -> DateTime:
    """
    Convert date/time with timezone to local timezone.
    """
    dt = coerce_to_pendulum(dt)
    tz = get_tz_local()
    return dt.in_tz(tz)


# =============================================================================
# Time differences
# =============================================================================

def get_duration_h_m(start: Union[str, DateTime],
                     end: Union[str, DateTime],
                     default: str = "N/A") -> str:
    """
    Calculate the time between two dates/times expressed as strings.

    Args:
        start: start date/time
        end: end date/time
        default: string value to return in case either of the inputs is
            ``None``

    Returns:
        a string that is one of

        .. code-block:

            'hh:mm'
            '-hh:mm'
            default

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
    Age (in whole years) at a particular date, or ``default``.

    Args:
        dob: date of birth
        when: date/time at which to calculate age
        default: value to return if either input is ``None``

    Returns:
        age in whole years (rounded down), or ``default``

    """
    dob = coerce_to_pendulum_date(dob)
    when = coerce_to_pendulum_date(when)
    if dob is None or when is None:
        return default
    return (when - dob).years


def pendulum_duration_from_timedelta(td: datetime.timedelta) -> Duration:
    """
    Converts a :class:`datetime.timedelta` into a :class:`pendulum.Duration`.

    .. code-block:: python

        from cardinal_pythonlib.datetimefunc import pendulum_duration_from_timedelta
        from datetime import timedelta
        from pendulum import Duration

        td1 = timedelta(days=5, hours=3, minutes=2, microseconds=5)
        d1 = pendulum_duration_from_timedelta(td1)
        
        td2 = timedelta(microseconds=5010293989234)
        d2 = pendulum_duration_from_timedelta(td2)

        td3 = timedelta(days=5000)
        d3 = pendulum_duration_from_timedelta(td3)
    """  # noqa
    return Duration(seconds=td.total_seconds())


def pendulum_duration_from_isodate_duration(dur: IsodateDuration) -> Duration:
    """
    Converts a :class:`isodate.isoduration.Duration` into a
    :class:`pendulum.Duration`.

    Both :class:`isodate.isoduration.Duration` and :class:`pendulum.Duration`
    incorporate an internal representation of a :class:`datetime.timedelta`
    (weeks, days, hours, minutes, seconds, milliseconds, microseconds) and
    separate representations of years and months.
    
    The :class:`isodate.isoduration.Duration` year/month elements are both of
    type :class:`decimal.Decimal` -- although its ``str()`` representation
    converts these silently to integer, which is quite nasty.
    
    If you create a Pendulum Duration it normalizes within its timedelta parts,
    but not across years and months. That is obviously because neither years
    and months are of exactly fixed duration.
    
    Raises:
        
        :exc:`ValueError` if the year or month component is not an integer

    .. code-block:: python

        from cardinal_pythonlib.datetimefunc import pendulum_duration_from_isodate_duration
        from isodate.isoduration import Duration as IsodateDuration
        from pendulum import Duration as PendulumDuration
        
        td1 = IsodateDuration(days=5, hours=3, minutes=2, microseconds=5)
        d1 = pendulum_duration_from_isodate_duration(td1)
        
        td2 = IsodateDuration(microseconds=5010293989234)
        d2 = pendulum_duration_from_isodate_duration(td2)
        
        td3 = IsodateDuration(days=5000)
        d3 = pendulum_duration_from_isodate_duration(td3)
        
        td4 = IsodateDuration(days=5000, years=5, months=2)
        d4 = pendulum_duration_from_isodate_duration(td4)
        # ... doesn't normalize across years/months; see explanation above
        
        td5 = IsodateDuration(days=5000, years=5.1, months=2.2)
        d5 = pendulum_duration_from_isodate_duration(td5)  # will raise
    """  # noqa
    y = dur.years
    if y.to_integral_value() != y:
        raise ValueError("Can't handle non-integer years {!r}".format(y))
    m = dur.months
    if m.to_integral_value() != m:
        raise ValueError("Can't handle non-integer months {!r}".format(y))
    return Duration(seconds=dur.tdelta.total_seconds(),
                    years=int(y),
                    months=int(m))


def duration_from_iso(iso_duration: str) -> Duration:
    """
    Converts an ISO-8601 format duration into a :class:`pendulum.Duration`.

    Raises:

        - :exc:`isodate.isoerror.ISO8601Error` for bad input
        - :exc:`ValueError` if the input had non-integer year or month values

    - The ISO-8601 duration format is ``P[n]Y[n]M[n]DT[n]H[n]M[n]S``; see
      https://en.wikipedia.org/wiki/ISO_8601#Durations.

    - ``pendulum.Duration.min`` and ``pendulum.Duration.max`` values are
      ``Duration(weeks=-142857142, days=-5)`` and ``Duration(weeks=142857142,
      days=6)`` respectively.

    - ``isodate`` supports negative durations of the format ``-P<something>``,
      such as ``-PT5S`` for "minus 5 seconds", but not e.g. ``PT-5S``.

    - I'm not clear if ISO-8601 itself supports negative durations. This
      suggests not: https://github.com/moment/moment/issues/2408. But lots of
      implementations (including to some limited extent ``isodate``) do support
      this concept.

    .. code-block:: python

        from pendulum import DateTime
        from cardinal_pythonlib.datetimefunc import duration_from_iso
        from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger
        main_only_quicksetup_rootlogger()

        d1 = duration_from_iso("P5W")
        d2 = duration_from_iso("P3Y1DT3H1M2S")
        d3 = duration_from_iso("P7000D")
        d4 = duration_from_iso("P1Y7000D")
        d5 = duration_from_iso("PT10053.22S")
        d6 = duration_from_iso("PT-10053.22S")  # raises ISO8601 error
        d7 = duration_from_iso("-PT5S")
        d7 = duration_from_iso("PT-5S")  # raises ISO8601 error
        now = DateTime.now()
        print(now)
        print(now + d1)
        print(now + d2)
        print(now + d3)
        print(now + d4)

    """
    duration = parse_duration(iso_duration)  # type: Union[datetime.timedelta, IsodateDuration]  # noqa
    if isinstance(duration, datetime.timedelta):
        result = pendulum_duration_from_timedelta(duration)
    elif isinstance(duration, IsodateDuration):
        result = pendulum_duration_from_isodate_duration(duration)
    else:
        raise AssertionError(
            "Bug in isodate.parse_duration, which returned unknown duration "
            "type: {!r}".format(duration))
    # log.debug("Converted {!r} -> {!r} -> {!r}".format(
    #     iso_duration, duration, result))
    return result


def duration_to_iso(d: Duration, permit_years_months: bool = True,
                    minus_sign_at_front: bool = True) -> str:
    """
    Converts a :class:`pendulum.Duration` into an ISO-8601 formatted string.
    
    Args:
        d:
            the duration

        permit_years_months:
            - if ``False``, durations with non-zero year or month components
              will raise a :exc:`ValueError`; otherwise, the ISO format will
              always be ``PT<seconds>S``.
            - if ``True``, year/month components will be accepted, and the
              ISO format will be ``P<years>Y<months>MT<seconds>S``.

        minus_sign_at_front:
            Applies to negative durations, which probably aren't part of the
            ISO standard.
            
            - if ``True``, the format ``-P<positive_duration>`` is used, i.e.
              with a minus sign at the front and individual components
              positive.
            - if ``False``, the format ``PT-<positive_seconds>S`` (etc.) is
              used, i.e. with a minus sign for each component. This format is
              not re-parsed successfully by ``isodate`` and will therefore
              fail :func:`duration_from_iso`.
              
    Raises:
        
        :exc:`ValueError` for bad input

    The maximum length of the resulting string (see test code below) is:
    
    - 21 if years/months are not permitted;
    - ill-defined if years/months are permitted, but 29 for much more than is
      realistic (negative, 1000 years, 11 months, and the maximum length for
      seconds/microseconds).

    .. code-block:: python

        from pendulum import DateTime, Duration
        from cardinal_pythonlib.datetimefunc import duration_from_iso, duration_to_iso
        from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger
        main_only_quicksetup_rootlogger()
        
        d1 = duration_from_iso("P5W")
        d2 = duration_from_iso("P3Y1DT3H1M2S")
        d3 = duration_from_iso("P7000D")
        d4 = duration_from_iso("P1Y7000D")
        d5 = duration_from_iso("PT10053.22S")
        print(duration_to_iso(d1))
        print(duration_to_iso(d2))
        print(duration_to_iso(d3))
        print(duration_to_iso(d4))
        print(duration_to_iso(d5))
        assert d1 == duration_from_iso(duration_to_iso(d1))
        assert d2 == duration_from_iso(duration_to_iso(d2))
        assert d3 == duration_from_iso(duration_to_iso(d3))
        assert d4 == duration_from_iso(duration_to_iso(d4))
        assert d5 == duration_from_iso(duration_to_iso(d5))
        strmin = duration_to_iso(Duration.min)  # '-P0Y0MT86399999913600.0S'
        strmax = duration_to_iso(Duration.max)  # 'P0Y0MT86400000000000.0S'
        duration_from_iso(strmin)  # raises ISO8601Error from isodate package (bug?)
        duration_from_iso(strmax)  # raises OverflowError from isodate package
        print(strmin)  # P0Y0MT-86399999913600.0S
        print(strmax)  # P0Y0MT86400000000000.0S
        d6 = duration_from_iso("P100Y999MT86400000000000.0S")  # OverflowError
        d7 = duration_from_iso("P0Y1MT86400000000000.0S")  # OverflowError
        d8 = duration_from_iso("P0Y1111111111111111MT76400000000000.0S")  # accepted!
        # ... length e.g. 38; see len(duration_to_iso(d8))
        
        # So the maximum string length may be ill-defined if years/months are
        # permitted (since Python 3 integers are unbounded; try 99 ** 10000). 
        # But otherwise:

        d9longest              = duration_from_iso("-P0Y0MT10000000000000.000009S")
        d10toolong             = duration_from_iso("-P0Y0MT100000000000000.000009S")  # fails, too many days
        assert d9longest == duration_from_iso(duration_to_iso(d9longest))
        
        d11longest_with_us     = duration_from_iso("-P0Y0MT1000000000.000009S")  # microseconds correct
        d12toolong_rounds_us   = duration_from_iso("-P0Y0MT10000000000.000009S")  # error in microseconds
        d13toolong_drops_us    = duration_from_iso("-P0Y0MT10000000000000.000009S")  # drops microseconds (within datetime.timedelta)
        d14toolong_parse_fails = duration_from_iso("-P0Y0MT100000000000000.000009S")  # fails, too many days
        assert d11longest_with_us == duration_from_iso(duration_to_iso(d11longest_with_us))
        assert d12toolong_rounds_us == duration_from_iso(duration_to_iso(d12toolong_rounds_us))
        assert d13toolong_drops_us == duration_from_iso(duration_to_iso(d13toolong_drops_us))
        
        longest_without_ym = duration_to_iso(d11longest_with_us, permit_years_months=False)
        print(longest_without_ym)  # -PT1000000000.000009S
        print(len(longest_without_ym))  # 21

        d15longest_realistic_with_ym_us = duration_from_iso("-P1000Y11MT1000000000.000009S")  # microseconds correct
        longest_realistic_with_ym = duration_to_iso(d15longest_realistic_with_ym_us)
        print(longest_realistic_with_ym)  # -P1000Y11MT1000000000.000009S
        print(len(longest_realistic_with_ym))  # 29
        
        # Now, double-check how the Pendulum classes handle year/month
        # calculations:
        basedate1 = DateTime(year=2000, month=1, day=1)  # 2000-01-01
        print(basedate1 + Duration(years=1))  # 2001-01-01; OK
        print(basedate1 + Duration(months=1))  # 2000-02-01; OK
        basedate2 = DateTime(year=2004, month=2, day=1)  # 2004-02-01; leap year
        print(basedate2 + Duration(years=1))  # 2005-01-01; OK
        print(basedate2 + Duration(months=1))  # 2000-03-01; OK
        print(basedate2 + Duration(months=1, days=1))  # 2000-03-02; OK

    """  # noqa
    prefix = ""
    negative = d < Duration()
    if negative and minus_sign_at_front:
        prefix = "-"
        d = -d
    if permit_years_months:
        return prefix + "P{years}Y{months}MT{seconds}S".format(
            years=d.years,
            months=d.months,
            seconds=d.total_seconds(),  # float
        )
    else:
        if d.years != 0:
            raise ValueError(
                "Duration has non-zero years: {!r}".format(d.years))
        if d.months != 0:
            raise ValueError(
                "Duration has non-zero months: {!r}".format(d.months))
        return prefix + "PT{seconds}S".format(seconds=d.total_seconds())


# =============================================================================
# Other manipulations
# =============================================================================

def truncate_date_to_first_of_month(
        dt: Optional[DateLikeType]) -> Optional[DateLikeType]:
    """
    Change the day to the first of the month.
    """
    if dt is None:
        return None
    return dt.replace(day=1)


# =============================================================================
# Older date/time functions for native Python datetime objects
# =============================================================================

def get_now_utc_notz_datetime() -> datetime.datetime:
    """
    Get the UTC time now, but with no timezone information,
    in :class:`datetime.datetime` format.
    """
    now = datetime.datetime.utcnow()
    return now.replace(tzinfo=None)


def coerce_to_datetime(x: Any) -> Optional[datetime.datetime]:
    """
    Ensure an object is a :class:`datetime.datetime`, or coerce to one, or
    raise :exc:`ValueError` or :exc:`OverflowError` (as per
    http://dateutil.readthedocs.org/en/latest/parser.html).
    """
    if x is None:
        return None
    elif isinstance(x, DateTime):
        return pendulum_to_datetime(x)
    elif isinstance(x, datetime.datetime):
        return x
    elif isinstance(x, datetime.date):
        return datetime.datetime(x.year, x.month, x.day)
    else:
        return dateutil.parser.parse(x)  # may raise
