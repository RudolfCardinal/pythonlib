#!/usr/bin/env python
# cardinal_pythonlib/datetimefunc.py

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
from string import Formatter
from typing import Any, Optional, Union

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

if Arrow is not None:
    PotentialDatetimeType = Union[
        None, datetime.datetime, datetime.date, DateTime, str, Arrow
    ]
    DateTimeLikeType = Union[datetime.datetime, DateTime, Arrow]
    DateLikeType = Union[datetime.date, DateTime, Arrow]
else:
    PotentialDatetimeType = Union[
        None, datetime.datetime, datetime.date, DateTime, str
    ]
    DateTimeLikeType = Union[datetime.datetime, DateTime]
    DateLikeType = Union[datetime.date, DateTime]

log = logging.getLogger(__name__)


# =============================================================================
# Coerce things to our favourite datetime class
# ... including adding timezone information to timezone-naive objects
# =============================================================================


def coerce_to_pendulum(
    x: PotentialDatetimeType, assume_local: bool = False
) -> Optional[DateTime]:
    """
    Converts something to a :class:`pendulum.DateTime`.

    Args:
        x:
            Something that may be coercible to a datetime.
        assume_local:
            Governs what happens if no timezone information is present in the
            source object. If ``True``, assume local timezone; if ``False``,
            assume UTC.

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
    tz_if_none_specified = get_tz_local() if assume_local else get_tz_utc()
    if isinstance(x, datetime.datetime):
        # noinspection PyTypeChecker
        return pendulum.instance(x, tz=tz_if_none_specified)  # (*)
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
        return pendulum.instance(dt, tz=tz_if_none_specified)  # (*)
    elif isinstance(x, str):
        # noinspection PyTypeChecker
        return pendulum.parse(x, tz=tz_if_none_specified)  # (*)  # may raise
    else:
        raise ValueError(f"Don't know how to convert to DateTime: {x!r}")
    # (*) If x already knew its timezone, it will not
    # be altered; "tz" will only be applied in the absence of other info.


def coerce_to_pendulum_date(
    x: PotentialDatetimeType, assume_local: bool = False, to_utc: bool = False
) -> Optional[Date]:
    """
    Converts something to a :class:`pendulum.Date`.

    Args:
        x:
            Something that may be coercible to a date.
        assume_local:
            Governs what happens if no timezone information is present in the
            source object. If ``True``, assume local timezone; if ``False``,
            assume UTC.
        to_utc:
            Should we return the date in UTC (e.g. London) (``True``), or the
            date in the timezone of the source (``False``)? For example,
            2022-02-27T23:00-05:00 (11pm in New York) is 2022-02-28T04:00Z (4am
            in London). Do you want the return value to be 27 Feb
            (``to_utc=False``) or 28 Feb (``to_utc=True``)?

    Returns:
        a :class:`pendulum.Date`, or ``None``.

    Raises:
        pendulum.parsing.exceptions.ParserError: if a string fails to parse
        ValueError: if no conversion possible
    """
    p = coerce_to_pendulum(x, assume_local=assume_local)
    if p is None:
        return None
    elif to_utc:
        return pendulum.UTC.convert(p).date()
    else:
        return p.date()


def pendulum_to_datetime(x: DateTime) -> datetime.datetime:
    """
    Used, for example, where a database backend insists on datetime.datetime.

    Compare code in :meth:`pendulum.datetime.DateTime.int_timestamp`.
    """
    return datetime.datetime(
        x.year,
        x.month,
        x.day,
        x.hour,
        x.minute,
        x.second,
        x.microsecond,
        tzinfo=x.tzinfo,
    )


def pendulum_to_datetime_stripping_tz(x: DateTime) -> datetime.datetime:
    """
    Converts a Pendulum ``DateTime`` to a ``datetime.datetime`` that has had
    timezone information stripped.
    """
    return datetime.datetime(
        x.year,
        x.month,
        x.day,
        x.hour,
        x.minute,
        x.second,
        x.microsecond,
        tzinfo=None,
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
        tzinfo=x.tzinfo,
    )


# =============================================================================
# Format dates/times/timedelta to strings
# =============================================================================


def format_datetime(
    d: PotentialDatetimeType, fmt: str, default: str = None
) -> Optional[str]:
    """
    Format a datetime with a ``strftime`` format specification string, or
    return ``default`` if the input is ``None``.
    """
    d = coerce_to_pendulum(d)
    if d is None:
        return default
    return d.strftime(fmt)


def strfdelta(
    tdelta: Union[datetime.timedelta, int, float, str],
    fmt="{D:02}d {H:02}h {M:02}m {S:02}s",
    inputtype="timedelta",
):
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
    if inputtype == "timedelta":
        remainder = int(tdelta.total_seconds())
    elif inputtype in ["s", "seconds"]:
        remainder = int(tdelta)
    elif inputtype in ["m", "minutes"]:
        remainder = int(tdelta) * 60
    elif inputtype in ["h", "hours"]:
        remainder = int(tdelta) * 3600
    elif inputtype in ["d", "days"]:
        remainder = int(tdelta) * 86400
    elif inputtype in ["w", "weeks"]:
        remainder = int(tdelta) * 604800
    else:
        raise ValueError(f"Bad inputtype: {inputtype}")

    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ("W", "D", "H", "M", "S")
    constants = {"W": 604800, "D": 86400, "H": 3600, "M": 60, "S": 1}
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


def get_duration_h_m(
    start: Union[str, DateTime],
    end: Union[str, DateTime],
    default: str = "N/A",
) -> str:
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


def get_age(
    dob: PotentialDatetimeType, when: PotentialDatetimeType, default: str = ""
) -> Union[int, str]:
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
        seconds=dur.tdelta.total_seconds(), years=int(y), months=int(m)
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
    duration = parse_duration(
        iso_duration
    )  # type: Union[datetime.timedelta, IsodateDuration]
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
            f"type: {duration!r}"
        )
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


def duration_to_iso(
    d: Duration,
    permit_years_months: bool = True,
    minus_sign_at_front: bool = True,
) -> str:
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
        # year/month information with the assumption that a year is 365 days
        # and a month is 30 days, which is perhaps a bit iffy.
        y = d.years
        m = d.months
        s = get_pendulum_duration_nonyear_nonmonth_seconds(d)
        return prefix + f"P{y}Y{m}MT{s}S"
    else:
        if d.years != 0:
            raise ValueError(f"Duration has non-zero years: {d.years!r}")
        if d.months != 0:
            raise ValueError(f"Duration has non-zero months: {d.months!r}")
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
    dt: Optional[DateLikeType],
) -> Optional[DateLikeType]:
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


def coerce_to_date(
    x: Any, assume_local: bool = False, to_utc: bool = False
) -> Optional[datetime.date]:
    """
    Ensure an object is a :class:`datetime.date`, or coerce to one, or
    raise :exc:`ValueError` or :exc:`OverflowError` (as per
    https://dateutil.readthedocs.org/en/latest/parser.html).

    See also :func:`coerce_to_pendulum_date`, noting that
    :class:`pendulum.Date` is a subclass of :class:`datetime.date`.
    """
    pd = coerce_to_pendulum_date(x, assume_local=assume_local, to_utc=to_utc)
    if pd is None:
        return None
    return pendulum_date_to_datetime_date(pd)
