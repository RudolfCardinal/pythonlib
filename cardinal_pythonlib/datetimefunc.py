#!/usr/bin/env python
# cardinal_pythonlib/datetimefunc.py

"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

**Support functions for date/time.**

Note regarding **durations**:

- ``datetime.timedelta`` takes parameters from microseconds to weeks; these
  are all exact.

- ``isodate.isoduration.Duration`` also includes years and months, which are
  well defined but not constant. It is explicit that it has two basic
  components: {year, month} and {timedelta}. Internally, it also treats years
  and months as separate.

- ``pendulum.Duration`` has the same span from microseconds to years, but it
  has internal assumptions (in v2.1.1+ at least) that a year is 365 days and
  a month is 30 days.


"""

import datetime
import logging
import sys
from string import Formatter
from typing import Any, Optional, Union
import unittest

import isodate.isoerror

try:
    # noinspection PyPackageRequirements
    from arrow import Arrow
except ImportError:
    Arrow = None

try:
    import dateutil.parser
except ImportError:
    dateutil = None

from isodate.isoduration import parse_duration, Duration as IsodateDuration
import pendulum
from pendulum import Date, DateTime, Duration, Time
from pendulum.tz import local_timezone
from pendulum.tz.timezone import Timezone

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

if Arrow is not None:
    PotentialDatetimeType = Union[None, datetime.datetime, datetime.date,
                                  DateTime, str, Arrow]
    DateTimeLikeType = Union[datetime.datetime, DateTime, Arrow]
    DateLikeType = Union[datetime.date, DateTime, Arrow]
else:
    PotentialDatetimeType = Union[None, datetime.datetime, datetime.date,
                                  DateTime, str]
    DateTimeLikeType = Union[datetime.datetime, DateTime]
    DateLikeType = Union[datetime.date, DateTime]

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
        # We use the standard python datetime.combine rather than the pendulum
        # DateTime.combine so that the tz will not be ignored in the call to
        # pendulum.instance
        dt = datetime.datetime.combine(x, midnight)
        # noinspection PyTypeChecker
        return pendulum.instance(dt, tz=tz)  # (*)
    elif isinstance(x, str):
        # noinspection PyTypeChecker
        return pendulum.parse(x, tz=tz)  # (*)  # may raise
    else:
        raise ValueError(f"Don't know how to convert to DateTime: {x!r}")
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
        hour=x.hour,
        minute=x.minute,
        second=x.second,
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
        raise ValueError(f"Bad inputtype: {inputtype}")

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
    """
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

    """
    y = dur.years
    if y.to_integral_value() != y:
        raise ValueError(f"Can't handle non-integer years {y!r}")
    m = dur.months
    if m.to_integral_value() != m:
        raise ValueError(f"Can't handle non-integer months {y!r}")
    return Duration(
        seconds=dur.tdelta.total_seconds(),
        years=int(y),
        months=int(m)
    )


def duration_from_iso(iso_duration: str) -> Duration:
    """
    Converts an ISO-8601 format duration into a :class:`pendulum.Duration`.

    Raises:

        - :exc:`isodate.isoerror.ISO8601Error` for bad input
        - :exc:`ValueError` if the input had non-integer year or month values

    - The ISO-8601 duration format is ``P[n]Y[n]M[n]DT[n]H[n]M[n]S``; see
      https://en.wikipedia.org/wiki/ISO_8601#Durations.

      - P = period, or duration designator, which comes first

        - [n]Y = number of years
        - [n]M = number of months
        - [n]W = number of weeks
        - [n]D = number of days

      - T = time designator (precedes the time component)

        - [n]H = number of hours
        - [n]M = number of minutes
        - [n]S = number of seconds

    - ``pendulum.Duration.min`` and ``pendulum.Duration.max`` values are
      ``Duration(weeks=-142857142, days=-5)`` and ``Duration(weeks=142857142,
      days=6)`` respectively.

    - ``isodate`` supports negative durations of the format ``-P<something>``,
      such as ``-PT5S`` for "minus 5 seconds", but not e.g. ``PT-5S``.

    - I'm not clear if ISO-8601 itself supports negative durations. This
      suggests not: https://github.com/moment/moment/issues/2408. But lots of
      implementations (including to some limited extent ``isodate``) do support
      this concept.

    """
    duration = parse_duration(iso_duration)  # type: Union[datetime.timedelta, IsodateDuration]  # noqa
    # print(f"CONVERTING: {iso_duration!r} -> {duration!r}")
    if isinstance(duration, datetime.timedelta):
        # It'll be a timedelta if it doesn't contain years or months.
        result = pendulum_duration_from_timedelta(duration)
    elif isinstance(duration, IsodateDuration):
        # It'll be a IsodateDuration if it contains years or months.
        result = pendulum_duration_from_isodate_duration(duration)
    else:
        raise AssertionError(
            f"Bug in isodate.parse_duration, which returned unknown duration "
            f"type: {duration!r}")
    # log.debug("Converted {!r} -> {!r} -> {!r}".format(
    #     iso_duration, duration, result))
    return result


def get_pendulum_duration_nonyear_nonmonth_seconds(d: Duration) -> float:
    """
    Returns the number of seconds in a :class:`pendulum.Duration` that are NOT
    part of its year/month representation.

    Before Pendulum 2.1.1, ``d.total_seconds()`` ignored year/month components,
    so this function will return the same as ``d.total_seconds()``.

    However, from Pendulum 2.1.1, ``total_seconds()`` incorporates year/month
    information with the assumption that a year is 365 days and a month is 30
    days, which is perhaps a bit iffy. This function removes that year/month
    component and returns the "remaining" seconds.
    """
    y = d.years
    m = d.months
    assumed_seconds_for_y_m = Duration(years=y, months=m).total_seconds()
    # ... for old Pendulum versions, that will be zero
    # ... for new Pendulum versions, that will be the number of seconds
    #     for that many years/months according to Pendulum's assumptions
    return d.total_seconds() - assumed_seconds_for_y_m


def duration_to_iso(d: Duration,
                    permit_years_months: bool = True,
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

    """  # noqa
    prefix = ""
    negative = d < Duration()
    if negative and minus_sign_at_front:
        prefix = "-"
        d = -d

    if permit_years_months:
        # Watch out here. Before Pendulum 2.1.1, d.total_seconds() ignored
        # year/month components. But from Pendulum 2.1.1, it incorporates
        # year/month information with the assumption that a year is 365 days and
        # a month is 30 days, which is perhaps a bit iffy.
        y = d.years
        m = d.months
        s = get_pendulum_duration_nonyear_nonmonth_seconds(d)
        return prefix + f"P{y}Y{m}MT{s}S"
    else:
        if d.years != 0:
            raise ValueError(
                f"Duration has non-zero years: {d.years!r}")
        if d.months != 0:
            raise ValueError(
                f"Duration has non-zero months: {d.months!r}")
        # At this point, it's easy. As there is no year/month component, (a) we
        # are confident we have an exact interval that is always validly
        # convertable to seconds, and (b) Pendulum versions before 2.1.1 and
        # from 2.1.1 onwards will give us the right number of seconds.
        s = d.total_seconds()
        return prefix + f"PT{s}S"


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
    https://dateutil.readthedocs.org/en/latest/parser.html).
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


# =============================================================================
# Unit testing
# =============================================================================

class TestCoerceToPendulum(unittest.TestCase):
    def test_returns_none_if_falsey(self) -> None:
        self.assertIsNone(coerce_to_pendulum(''))

    def test_returns_input_if_pendulum_datetime(self) -> None:
        datetime_in = DateTime.now()
        datetime_out = coerce_to_pendulum(datetime_in)

        self.assertIs(datetime_in, datetime_out)

    def test_converts_python_datetime_with_local_tz(self) -> None:
        datetime_in = datetime.datetime(2020, 6, 15, hour=15, minute=42)
        datetime_out = coerce_to_pendulum(datetime_in, assume_local=True)

        self.assertIsInstance(datetime_out, DateTime)
        self.assertTrue(datetime_out.is_local())

    def test_converts_python_datetime_with_utc_tz(self) -> None:
        datetime_in = datetime.datetime(2020, 6, 15, hour=15, minute=42)
        datetime_out = coerce_to_pendulum(datetime_in)

        self.assertIsInstance(datetime_out, DateTime)
        self.assertTrue(datetime_out.is_utc())

    def test_converts_python_datetime_with_tz(self) -> None:
        utc_offset = datetime.timedelta(hours=5, minutes=30)
        datetime_in = datetime.datetime(
            2020, 6, 15, hour=15, minute=42,
            tzinfo=datetime.timezone(utc_offset)
        )
        datetime_out = coerce_to_pendulum(datetime_in)

        self.assertIsInstance(datetime_out, DateTime)
        self.assertEqual(datetime_out.utcoffset(), utc_offset)

    def test_converts_python_date_with_local_tz(self) -> None:
        date_in = datetime.date(2020, 6, 15)
        datetime_out = coerce_to_pendulum(date_in, assume_local=True)

        self.assertIsInstance(datetime_out, DateTime)
        self.assertTrue(datetime_out.is_local())

    def test_converts_python_date_with_utc_tz(self) -> None:
        date_in = datetime.date(2020, 6, 15)
        datetime_out = coerce_to_pendulum(date_in)

        self.assertIsInstance(datetime_out, DateTime)
        self.assertTrue(datetime_out.is_utc())

    def test_parses_datetime_string_with_tz(self) -> None:
        datetime_in = "2020-06-15T14:52:36+05:30"
        datetime_out = coerce_to_pendulum(datetime_in)

        self.assertIsInstance(datetime_out, DateTime)
        self.assertEqual(
            datetime_out.utcoffset(),
            datetime.timedelta(hours=5, minutes=30)
        )

    def test_parses_datetime_string_with_utc_tz(self) -> None:
        datetime_in = "2020-06-15T14:52:36"
        datetime_out = coerce_to_pendulum(datetime_in)

        self.assertIsInstance(datetime_out, DateTime)
        self.assertTrue(datetime_out.is_utc())

    def test_parses_datetime_string_with_local_tz(self) -> None:
        datetime_in = "2020-06-15T14:52:36"
        datetime_out = coerce_to_pendulum(datetime_in, assume_local=True)

        self.assertIsInstance(datetime_out, DateTime)
        self.assertTrue(datetime_out.is_local())

    def test_raises_if_type_invalid(self) -> None:
        with self.assertRaises(ValueError) as cm:
            # noinspection PyTypeChecker
            coerce_to_pendulum(12345)

        self.assertIn(
            "Don't know how to convert to DateTime", str(cm.exception)
        )


class TestDurations(unittest.TestCase):

    # -------------------------------------------------------------------------
    # ISO duration conversion
    # -------------------------------------------------------------------------
    def _assert_iso_converts(self, iso_duration: str) -> None:
        """
        Checks that the conversions work.

        Remember, ISO-8601 durations are non-unique.
        """
        d1 = duration_from_iso(iso_duration)
        i2 = duration_to_iso(d1)
        d2 = duration_from_iso(i2)

        self.assertEqual(
            d1,
            d2,
            f"Failed conversion {iso_duration!r} -> {d1!r} -> {i2!r} -> {d2!r}"
        )

    def _assert_bad_iso(self, iso_duration: str) -> None:
        with self.assertRaises(isodate.isoerror.ISO8601Error):
            duration_from_iso(iso_duration)

    def _assert_iso_overflows(self, iso_duration: str) -> None:
        """
        Check for ISO-8601 duration values that overflow, by raising
        :exc:`OverflowError` from the ``isodate`` package.
        """
        with self.assertRaises(OverflowError):
            duration_from_iso(iso_duration)

    def _assert_iso_microsecond_fails(self,
                                      iso_duration: str,
                                      correct_microseconds: int) -> None:
        """
        For conversions that do NOT work.
        """
        d1 = duration_from_iso(iso_duration)
        self.assertNotEqual(
            d1.microseconds,
            correct_microseconds,
            f"Unexpected microsecond success: {iso_duration!r} -> {d1!r}"
        )

    def assert_isodateduration_eq_pendulumduration(
            self, i: isodate.Duration, p: Duration) -> None:
        # We test via a timedelta class.
        start = datetime.datetime(year=1970, month=1, day=1)
        # ... an start time used transiently by isodate.Duration.totimedelta
        # which makes its "year" and "month" aspects true.
        end_i = start + i
        end_p = pendulum_to_datetime_stripping_tz(
            coerce_to_pendulum(start) + p
        )
        self.assertEqual(
            end_i,
            end_p,
            f"From a starting point of {start}, "
            f"{i!r} -> {end_i!r} != "
            f"{p!r} -> {end_p!r}."
        )

    def test_duration_conversions_from_iso(self) -> None:
        """
        Check a range of ISO-8601 duration representations, converting them
        to/from Python duration objects.
        """
        self._assert_iso_converts("P5W")
        self._assert_iso_converts("P3Y1DT3H1M2S")
        self._assert_iso_converts("P7000D")
        self._assert_iso_converts("P1Y7000D")
        self._assert_iso_converts("PT10053.22S")

        # A negative one:
        self._assert_iso_converts("-PT5S")

        # Bad ones:
        self._assert_bad_iso("PT-5S")

        strmin = duration_to_iso(Duration.min)  # '-P0Y0MT86399999913600.0S'
        self._assert_iso_converts(strmin)

        strmax = duration_to_iso(Duration.max)  # 'P0Y0MT86400000000000.0S'
        self._assert_iso_overflows(strmax)

        self._assert_iso_overflows("P100Y999MT86400000000000.0S")
        self._assert_iso_overflows("P0Y1MT86400000000000.0S")

        i8long = "P0Y1111111111111111MT76400000000000.0S"
        # That worked with Pendulum <2.1.1, but not with 2.1.1+.
        self._assert_iso_overflows(i8long)

        # So the maximum string length may be ill-defined if years/months are
        # permitted (since Python 3 integers are unbounded; try 99 ** 10000).
        # But otherwise:

        self._assert_iso_overflows("-P0Y0MT100000000000000.000009S")
        # too many days

        # Longest thing that works (with zero years/months):
        i9longest = "-P0Y0MT10000000000000.000009S"
        self._assert_iso_converts(i9longest)
        longest_feasible_iso_duration_no_year_month = 29
        self.assertEqual(
            len(i9longest),
            longest_feasible_iso_duration_no_year_month
        )

        i11longest_with_us = "-P0Y0MT1000000000.000009S"
        self._assert_iso_converts(i11longest_with_us)  # microseconds correct

        i12toolong_rounds_us = "-P0Y0MT10000000000.000009S"
        self._assert_iso_microsecond_fails(
            i12toolong_rounds_us, correct_microseconds=9)
        self._assert_iso_converts(i12toolong_rounds_us)

        i13toolong_drops_us = "-P0Y0MT10000000000000.000009S"
        self._assert_iso_microsecond_fails(
            i13toolong_drops_us, correct_microseconds=9)
        # ... drops microseconds (within datetime.timedelta)
        self._assert_iso_converts(i13toolong_drops_us)

        i14toolong_parse_fails = "-P0Y0MT100000000000000.000009S"
        self._assert_iso_overflows(i14toolong_parse_fails)  # too many days

        longest_without_ym = duration_to_iso(
            duration_from_iso(i11longest_with_us),
            permit_years_months=False
        )
        assert longest_without_ym == "-PT1000000000.000009S"
        assert len(longest_without_ym) == 21
        self._assert_iso_converts(longest_without_ym)

        # todo: This one doesn't convert properly:
        # i15longest_realistic_with_ym_us = "-P1000Y11MT1000000000.000009S"
        # assert len(i15longest_realistic_with_ym_us) == 29
        # self._assert_iso_converts(i15longest_realistic_with_ym_us)

    # -------------------------------------------------------------------------
    # datetime.timedelta versus pendulum.Duration
    # -------------------------------------------------------------------------

    def _check_td_to_pd(self, td: datetime.timedelta) -> None:
        pd = pendulum_duration_from_timedelta(td)
        self.assertEqual(
            td.total_seconds(),
            pd.total_seconds(),
            f"{td!r}.total_seconds() != {pd!r}.total_seconds()"
        )

    def test_pendulum_duration_from_timedelta(self) -> None:
        self._check_td_to_pd(
            datetime.timedelta(days=5, hours=3, minutes=2, microseconds=5)
        )
        self._check_td_to_pd(
            datetime.timedelta(microseconds=5010293989234)
        )
        self._check_td_to_pd(
            datetime.timedelta(days=5000)
        )

    # -------------------------------------------------------------------------
    # isodate.isoduration.Duration versus pendulum.Duration
    # -------------------------------------------------------------------------

    def test_isodate_pendulum_duration_equivalence(self) -> None:
        """
        Check that our IsodateDuration and Duration objects are being handled
        equivalently.
        """
        self.assert_isodateduration_eq_pendulumduration(
            IsodateDuration(years=1, seconds=1),
            Duration(years=1, seconds=1)
        )

    def _check_id_to_pd(self, isodur: IsodateDuration) -> None:
        pendur = pendulum_duration_from_isodate_duration(isodur)
        self.assertEqual(
            isodur.years,
            pendur.years,
            f"Year mismatch: {isodur!r} -> {isodur.years!r} != "
            f"{pendur!r} -> {pendur.years!r}"
        )
        self.assertEqual(
            isodur.months,
            pendur.months,
            f"Month mismatch: {isodur!r} -> {isodur.months!r} != "
            f"{pendur!r} -> {pendur.months!r}"
        )
        id_non_ym_seconds = isodur.tdelta.total_seconds()
        pd_non_ym_seconds = get_pendulum_duration_nonyear_nonmonth_seconds(
            pendur)
        self.assertEqual(
            id_non_ym_seconds,
            pd_non_ym_seconds,
            f"Seconds mismatch (ignoring year/month component): "
            f"{isodur!r} -> {id_non_ym_seconds} != "
            f"{pendur!r} -> {pd_non_ym_seconds!r}"
        )

    def test_pendulum_duration_from_isodate_duration(self) -> None:
        self._check_id_to_pd(
            IsodateDuration(days=5, hours=3, minutes=2, microseconds=5)
        )
        self._check_id_to_pd(
            IsodateDuration(microseconds=5010293989234)
        )
        self._check_id_to_pd(
            IsodateDuration(days=5000)
        )
        self._check_id_to_pd(
            IsodateDuration(days=5000, years=5, months=2)
            # ... doesn't normalize across years/months; see explanation above
        )
        with self.assertRaises(ValueError):
            pendulum_duration_from_isodate_duration(
                IsodateDuration(days=5000, years=5.1, months=2.2)
            )

    # -------------------------------------------------------------------------
    # pendulum.Duration arithmetic
    # -------------------------------------------------------------------------

    def test_pendulum_arithmetic(self) -> None:
        # Now, double-check how the Pendulum classes handle year/month
        # calculations:
        basedate1 = DateTime(year=2000, month=1, day=1)  # 2000-01-01
        self.assertEqual(
            basedate1 + Duration(years=1),
            DateTime(year=2001, month=1, day=1)
        )
        self.assertEqual(
            basedate1 + Duration(months=1),
            DateTime(year=2000, month=2, day=1)
        )
        basedate2 = DateTime(year=2004, month=2, day=1)  # 2004-02-01; leap year
        self.assertEqual(
            basedate2 + Duration(years=1),
            DateTime(year=2005, month=2, day=1)
        )
        self.assertEqual(
            basedate2 + Duration(months=1),
            DateTime(year=2004, month=3, day=1)
        )
        self.assertEqual(
            basedate2 + Duration(months=1, days=1),
            DateTime(year=2004, month=3, day=2)
        )


# =============================================================================
# main
# =============================================================================

if __name__ == "__main__":
    main_only_quicksetup_rootlogger(level=logging.DEBUG)
    log.info("Running unit tests")
    unittest.main(argv=[sys.argv[0]])
    sys.exit(0)
