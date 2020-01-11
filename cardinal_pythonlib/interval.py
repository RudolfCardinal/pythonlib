#!/usr/bin/env python
# cardinal_pythonlib/interval.py

"""
===============================================================================

    Original code copyright (C) 2009-2020 Rudolf Cardinal (rudolf@pobox.com).

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

**Time interval classes and related functions.**

"""

# =============================================================================
# Imports
# =============================================================================

import datetime
import logging
import sys
from typing import List, Optional, Set, Tuple, Union
import unittest

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

log = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7
DAYS_PER_YEAR = 365  # approx...

SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR
SECONDS_PER_DAY = SECONDS_PER_HOUR * HOURS_PER_DAY
SECONDS_PER_WEEK = SECONDS_PER_DAY * DAYS_PER_WEEK
SECONDS_PER_YEAR = SECONDS_PER_DAY * DAYS_PER_YEAR  # approx...

NORMAL_DAY_START_H = 7
NORMAL_DAY_END_H = 19

BANK_HOLIDAYS = [datetime.datetime.strptime(x, "%Y-%m-%d").date() for x in [
    # https://www.gov.uk/bank-holidays
    # All bank holiday dates vary, even the date-based ones; e.g. if Christmas
    # Day is a Sunday, then the Christmas Day substitute bank holiday is Tue 27
    # Dec, after the Boxing Day Monday bank holiday.

    # 2014
    "2014-01-01",  # New Year's Day
    "2014-04-18",  # Good Friday
    "2014-04-21",  # Easter Monday
    "2014-05-05",  # Early May Bank Holiday
    "2014-05-26",  # Spring Bank Holiday
    "2014-08-25",  # Summer Bank Holiday
    "2014-12-25",  # Christmas Day
    "2014-12-26",  # Boxing Day
    # 2015
    "2015-01-01",  # New Year's Day
    "2015-04-03",  # Good Friday
    "2015-04-06",  # Easter Monday
    "2015-05-04",  # Early May Bank Holiday
    "2015-05-25",  # Spring Bank Holiday
    "2015-08-31",  # Summer Bank Holiday
    "2015-12-25",  # Christmas Day
    "2015-12-28",  # Boxing Day (substitute)
    # 2016
    "2016-01-01",  # New Year's Day
    "2016-03-25",  # Good Friday
    "2016-03-28",  # Easter Monday
    "2016-05-02",  # Early May Bank Holiday
    "2016-05-30",  # Spring Bank Holiday
    "2016-08-29",  # Summer Bank Holiday
    "2016-12-26",  # Boxing Day
    "2016-12-27",  # Christmas Day (substitute)
    # 2017
    "2017-01-02",  # New Year's Day (substitute day)
    "2017-04-14",  # Good Friday
    "2017-04-17",  # Easter Monday
    "2017-05-01",  # Early May bank holiday
    "2017-05-29",  # Spring bank holiday
    "2017-08-28",  # Summer bank holiday
    "2017-12-25",  # Christmas Day
    "2017-12-26",  # Boxing Day
    # 2018
    "2018-01-01",  # New Year's Day
    "2018-03-30",  # Good Friday
    "2018-04-02",  # Easter Monday
    "2018-05-07",  # Early May bank holiday
    "2018-05-28",  # Spring bank holiday
    "2018-08-28",  # Summer bank holiday
    "2018-12-25",  # Christmas Day
    "2018-12-26",  # Boxing Day
    # 2019
    "2019-01-01",  # New Year's Day
    "2019-04-19",  # Good Friday
    "2019-04-22",  # Easter Monday
    "2019-05-06",  # Early May bank holiday
    "2019-05-27",  # Spring bank holiday
    "2019-08-26",  # Summer bank holiday
    "2019-12-25",  # Christmas Day
    "2019-12-26",  # Boxing Day

    # Don't forget to add more in years to come.
]]


# =============================================================================
# Helper functions
# =============================================================================

def formatdt(date: datetime.date, include_time: bool = True) -> str:
    """
    Formats a ``datetime.date`` to ISO-8601 basic format, to minute accuracy
    with no timezone (or, if ``include_time`` is ``False``, omit the time).
    """
    if include_time:
        return date.strftime("%Y-%m-%dT%H:%M")
    else:
        return date.strftime("%Y-%m-%d")


def convert_duration(duration: datetime.timedelta,
                     units: str) -> Optional[float]:
    """
    Convert a ``datetime.timedelta`` object -- a duration -- into other
    units. Possible units:

        ``s``, ``sec``, ``seconds``
        ``m``, ``min``, ``minutes``
        ``h``, ``hr``, ``hours``
        ``d``, ``days``
        ``w``, ``weeks``
        ``y``, ``years``
    """
    if duration is None:
        return None
    s = duration.total_seconds()
    if units in ['s', 'sec', 'seconds']:
        return s
    if units in ['m', 'min', 'minutes']:
        return s / SECONDS_PER_MINUTE
    if units in ['h', 'hr', 'hours']:
        return s / SECONDS_PER_HOUR
    if units in ['d', 'days']:
        return s / SECONDS_PER_DAY
    if units in ['w', 'weeks']:
        return s / SECONDS_PER_WEEK
    if units in ['y', 'years']:
        return s / SECONDS_PER_YEAR
    raise ValueError(f"Unknown units: {units}")


def is_bank_holiday(date: datetime.date) -> bool:
    """
    Is the specified date (a ``datetime.date`` object) a UK bank holiday?

    Uses the ``BANK_HOLIDAYS`` list.
    """
    return date in BANK_HOLIDAYS


def is_weekend(date: datetime.date) -> bool:
    """
    Is the specified date (a ``datetime.date`` object) a weekend?
    """
    return date.weekday() in [5, 6]


def is_saturday(date: datetime.date) -> bool:
    """
    Is the specified date (a ``datetime.date`` object) a Saturday?
    """
    return date.weekday() == 5


def is_sunday(date: datetime.date) -> bool:
    """
    Is the specified date (a ``datetime.date`` object) a Sunday?
    """
    return date.weekday() == 6


def is_normal_working_day(date: datetime.date) -> bool:
    """
    Is the specified date (a ``datetime.date`` object) a normal working day,
    i.e. not a weekend or a bank holiday?
    """
    return not(is_weekend(date) or is_bank_holiday(date))


# =============================================================================
# Interval
# =============================================================================

class Interval(object):
    """
    Object representing a time interval, with start and end objects that are
    normally ``datetime.datetime`` objects (though with care, a subset of some
    methods are possible with ``datetime.date`` objects; caveat emptor, and
    some methods will crash).

    Does not handle open-ended intervals (−∞, +∞) or null intervals.

    There's probably an existing class for this...
    """

    def __init__(self, start: datetime.datetime,
                 end: datetime.datetime) -> None:
        """
        Creates the interval.
        """
        if start is None or end is None:
            raise TypeError("Invalid interval creation")
        if start > end:
            (start, end) = (end, start)
        self.start = start
        self.end = end

    def __repr__(self) -> str:
        """
        Returns the canonical string representation of the object.
        """
        return f"Interval(start={self.start!r}, end={self.end!r})"

    def __str__(self) -> str:
        """
        Returns a string representation of the object.
        """
        return f"{formatdt(self.start)} − {formatdt(self.end)}"

    def __add__(self, value: datetime.timedelta) -> "Interval":
        """
        Adds a constant (``datetime.timedelta`` object) to the interval's start
        and end. Returns the new :class:`Interval`.
        """
        return Interval(self.start + value, self.end + value)

    def __lt__(self, other: "Interval") -> bool:
        """
        Allows sorting (on start time).
        """
        return self.start < other.start

    def copy(self) -> "Interval":
        """
        Returns a copy of the interval.
        """
        return Interval(self.start, self.end)

    def overlaps(self, other: "Interval") -> bool:
        """
        Does this interval overlap the other?

        Overlap:

        .. code-block:: none

            S--------S     S---S            S---S
              O---O          O---O        O---O

        Simpler method of testing is for non-overlap!

        .. code-block:: none

            S---S              S---S
                O---O      O---O
        """
        return not(self.end <= other.start or self.start >= other.end)

    def contiguous(self, other: "Interval") -> bool:
        """
        Does this interval overlap or touch the other?
        """
        return not(self.end < other.start or self.start > other.end)

    def contains(self, time: datetime.datetime,
                 inclusive: bool = True) -> bool:
        """
        Does the interval contain a momentary time?

        Args:
            time: the ``datetime.datetime`` to check
            inclusive: use inclusive rather than exclusive range checks?
        """
        if inclusive:
            return self.start <= time <= self.end
        else:
            return self.start < time < self.end

    def within(self, other: "Interval", inclusive: bool = True) -> bool:
        """
        Is this interval contained within the other?

        Args:
            other: the :class:`Interval` to check
            inclusive: use inclusive rather than exclusive range checks?
        """
        if not other:
            return False
        if inclusive:
            return self.start >= other.start and self.end <= other.end
        else:
            return self.start > other.start and self.end < other.end

    def union(self, other: "Interval") -> "Interval":
        """
        Returns an interval spanning the extent of this and the ``other``.
        """
        return Interval(
            min(self.start, other.start),
            max(self.end, other.end)
        )

    def intersection(self, other: "Interval") -> Optional["Interval"]:
        """
        Returns an :class:`Interval` representing the intersection of this and
        the ``other``, or ``None`` if they don't overlap.
        """
        if not self.contiguous(other):
            return None
        return Interval(
            max(self.start, other.start),
            min(self.end, other.end)
        )

    def cut(self, times: Union[datetime.datetime,
                               List[datetime.datetime]]) -> List["Interval"]:
        """
        Returns a list of intervals produced by using times (a list of
        ``datetime.datetime`` objects, or a single such object) as a set of
        knives to slice this interval.
        """
        if not isinstance(times, list):
            # Single time
            time = times
            if not self.contains(time):
                return []
            return [
                Interval(self.start, time),
                Interval(time, self.end)
            ]
        else:
            # Multiple times
            times = [t for t in times if self.contains(t)]  # discard others
            times.sort()
            times = [self.start] + times + [self.end]
            intervals = []
            for i in range(len(times) - 1):
                intervals.append(Interval(times[i], times[i + 1]))
            return intervals

    def duration(self) -> datetime.timedelta:
        """
        Returns a datetime.timedelta object representing the duration of this
        interval.
        """
        return self.end - self.start

    def duration_in(self, units: str) -> float:
        """
        Returns the duration of this interval in the specified units, as
        per :func:`convert_duration`.
        """
        return convert_duration(self.duration(), units)

    @staticmethod
    def wholeday(date: datetime.date) -> "Interval":
        """
        Returns an :class:`Interval` covering the date given (midnight at the
        start of that day to midnight at the start of the next day).
        """
        start = datetime.datetime.combine(date, datetime.time())
        return Interval(
            start,
            start + datetime.timedelta(days=1)
        )

    @staticmethod
    def daytime(date: datetime.date,
                daybreak: datetime.time = datetime.time(NORMAL_DAY_START_H),
                nightfall: datetime.time = datetime.time(NORMAL_DAY_END_H)) \
            -> "Interval":
        """
        Returns an :class:`Interval` representing daytime on the date given.
        """
        return Interval(
            datetime.datetime.combine(date, daybreak),
            datetime.datetime.combine(date, nightfall),
        )

    @staticmethod
    def dayspan(startdate: datetime.date,
                enddate: datetime.date,
                include_end: bool = True) -> Optional["Interval"]:
        """
        Returns an :class:`Interval` representing the date range given, from
        midnight at the start of the first day to midnight at the end of the
        last (i.e. at the start of the next day after the last), or if
        include_end is False, 24h before that.

        If the parameters are invalid, returns ``None``.
        """
        if enddate < startdate:
            return None
        if enddate == startdate and include_end:
            return None
        start_dt = datetime.datetime.combine(startdate, datetime.time())
        end_dt = datetime.datetime.combine(enddate, datetime.time())
        if include_end:
            end_dt += datetime.timedelta(days=1)
        return Interval(start_dt, end_dt)

    def component_on_date(self, date: datetime.date) -> Optional["Interval"]:
        """
        Returns the part of this interval that falls on the date given, or
        ``None`` if the interval doesn't have any part during that date.
        """
        return self.intersection(Interval.wholeday(date))

    def day_night_duration(
            self,
            daybreak: datetime.time = datetime.time(NORMAL_DAY_START_H),
            nightfall: datetime.time = datetime.time(NORMAL_DAY_END_H)) \
            -> Tuple[datetime.timedelta, datetime.timedelta]:
        """
        Returns a ``(day, night)`` tuple of ``datetime.timedelta`` objects
        giving the duration of this interval that falls into day and night
        respectively.
        """
        daytotal = datetime.timedelta()
        nighttotal = datetime.timedelta()
        startdate = self.start.date()
        enddate = self.end.date()
        ndays = (enddate - startdate).days + 1
        for i in range(ndays):
            date = startdate + datetime.timedelta(days=i)
            component = self.component_on_date(date)
            # ... an interval on a single day
            day = Interval.daytime(date, daybreak, nightfall)
            daypart = component.intersection(day)
            if daypart is not None:
                daytotal += daypart.duration()
                nighttotal += component.duration() - daypart.duration()
            else:
                nighttotal += component.duration()
        return daytotal, nighttotal

    def duration_outside_nwh(
            self,
            starttime: datetime.time = datetime.time(NORMAL_DAY_START_H),
            endtime: datetime.time = datetime.time(NORMAL_DAY_END_H),
            weekdays_only: bool = False,
            weekends_only: bool = False) -> datetime.timedelta:
        """
        Returns a duration (a ``datetime.timedelta`` object) representing the
        number of hours outside normal working hours.

        This is not simply a subset of :meth:`day_night_duration`, because
        weekends are treated differently (they are always out of hours).

        The options allow the calculation of components on weekdays or weekends
        only.
        """
        if weekdays_only and weekends_only:
            raise ValueError("Can't have weekdays_only and weekends_only")
        ooh = datetime.timedelta()  # ooh = out of (normal) hours
        startdate = self.start.date()
        enddate = self.end.date()
        ndays = (enddate - startdate).days + 1
        for i in range(ndays):
            date = startdate + datetime.timedelta(days=i)
            component = self.component_on_date(date)
            # ... an interval on a single day
            if not is_normal_working_day(date):
                if weekdays_only:
                    continue
                ooh += component.duration()  # all is out-of-normal-hours
            else:
                if weekends_only:
                    continue
                normalday = Interval.daytime(date, starttime, endtime)
                normalpart = component.intersection(normalday)
                if normalpart is not None:
                    ooh += component.duration() - normalpart.duration()
                else:
                    ooh += component.duration()
        return ooh

    def n_weekends(self) -> int:
        """
        Returns the number of weekends that this interval covers. Includes
        partial weekends.
        """
        startdate = self.start.date()
        enddate = self.end.date()
        ndays = (enddate - startdate).days + 1
        in_weekend = False
        n_weekends = 0
        for i in range(ndays):
            date = startdate + datetime.timedelta(days=i)
            if not in_weekend and is_weekend(date):
                in_weekend = True
                n_weekends += 1
            elif in_weekend and not is_weekend(date):
                in_weekend = False
        return n_weekends

    def saturdays_of_weekends(self) -> Set[datetime.date]:
        """
        Returns the dates of all Saturdays that are part of weekends that this
        interval covers (each Saturday representing a unique identifier for
        that weekend). The Saturday itself isn't necessarily the part of the
        weekend that the interval covers!
        """
        startdate = self.start.date()
        enddate = self.end.date()
        ndays = (enddate - startdate).days + 1
        saturdays = set()
        for i in range(ndays):
            date = startdate + datetime.timedelta(days=i)
            if is_saturday(date):
                saturdays.add(date)
            elif is_sunday(date):
                saturdays.add(date - datetime.timedelta(days=1))
        return saturdays


# =============================================================================
# IntervalList
# =============================================================================

class IntervalList(object):
    """
    Object representing a list of Intervals.
    Maintains an internally sorted state (by interval start time).
    """

    _ONLY_FOR_NO_INTERVAL = (
        "Only implemented for IntervalList objects with no_overlap == True"
    )

    # -------------------------------------------------------------------------
    # Constructor, representations, copying
    # -------------------------------------------------------------------------

    def __init__(self,
                 intervals: List[Interval] = None,
                 no_overlap: bool = True,
                 no_contiguous: bool = True) -> None:
        """
        Creates the :class:`IntervalList`.

        Args:
            intervals: optional list of :class:`Interval` objects to
                incorporate into the :class:`IntervalList`
            no_overlap: merge intervals that overlap (now and on subsequent
                addition)?
            no_contiguous: if ``no_overlap`` is set, merge intervals that are
                contiguous too?
        """
        # DO NOT USE intervals=[] in the function signature; that's the route
        # to a mutable default and a huge amount of confusion as separate
        # objects appear non-independent.
        self.intervals = [] if intervals is None else list(intervals)
        self.no_overlap = no_overlap
        self.no_contiguous = no_contiguous
        for i in self.intervals:
            if not isinstance(i, Interval):
                raise TypeError(
                    f"IntervalList creation failed: contents are not all "
                    f"Interval: {self.intervals!r}")
        self._tidy()

    def __repr__(self) -> str:
        """
        Returns the canonical string representation of the object.
        """
        return (
            f"IntervalList(intervals={self.intervals!r}, "
            f"no_overlap={self.no_overlap}, "
            f"no_contiguous={self.no_contiguous})")

    def copy(self, no_overlap: bool = None,
             no_contiguous: bool = None) -> "IntervalList":
        """
        Makes and returns a copy of the :class:`IntervalList`. The
        ``no_overlap``/``no_contiguous`` parameters can be changed.

        Args:
            no_overlap: merge intervals that overlap (now and on subsequent
                addition)?
            no_contiguous: if ``no_overlap`` is set, merge intervals that are
                contiguous too?
        """
        if no_overlap is None:
            no_overlap = self.no_overlap
        if no_contiguous is None:
            no_contiguous = self.no_contiguous
        return IntervalList(self.intervals, no_overlap=no_overlap,
                            no_contiguous=no_contiguous)

    def list(self) -> List[Interval]:
        """
        Returns the contained list of :class:`Interval` objects.
        """
        return self.intervals

    # -------------------------------------------------------------------------
    # Add an interval
    # -------------------------------------------------------------------------

    def add(self, interval: Interval) -> None:
        """
        Adds an interval to the list. If ``self.no_overlap`` is True, as is the
        default, it will merge any overlapping intervals thus created.
        """
        if interval is None:
            return
        if not isinstance(interval, Interval):
            raise TypeError(
                "Attempt to insert non-Interval into IntervalList")
        self.intervals.append(interval)
        self._tidy()

    # -------------------------------------------------------------------------
    # Internal consolidation functions, and sorting
    # -------------------------------------------------------------------------

    def _tidy(self) -> None:
        """
        Removes overlaps, etc., and sorts.
        """
        if self.no_overlap:
            self.remove_overlap(self.no_contiguous)  # will sort
        else:
            self._sort()

    def _sort(self) -> None:
        """
        Sorts (in place) by interval start time.
        """
        self.intervals.sort()

    def _remove_overlap_sub(self, also_remove_contiguous: bool) -> bool:
        """
        Called by :meth:`remove_overlap`. Removes the first overlap found.

        Args:
            also_remove_contiguous: treat contiguous (as well as overlapping)
                intervals as worthy of merging?

        Returns:
            bool: ``True`` if an overlap was removed; ``False`` otherwise

        """
        # Returns
        for i in range(len(self.intervals)):
            for j in range(i + 1, len(self.intervals)):
                first = self.intervals[i]
                second = self.intervals[j]
                if also_remove_contiguous:
                    test = first.contiguous(second)
                else:
                    test = first.overlaps(second)
                if test:
                    newint = first.union(second)
                    self.intervals.pop(j)
                    self.intervals.pop(i)  # note that i must be less than j
                    self.intervals.append(newint)
                    return True
        return False

    def remove_overlap(self, also_remove_contiguous: bool = False) -> None:
        """
        Merges any overlapping intervals.

        Args:
            also_remove_contiguous: treat contiguous (as well as overlapping)
                intervals as worthy of merging?
        """
        overlap = True
        while overlap:
            overlap = self._remove_overlap_sub(also_remove_contiguous)
        self._sort()

    def _any_overlap_or_contiguous(self, test_overlap: bool) -> bool:
        """
        Do any of the intervals overlap?

        Args:
            test_overlap: if ``True``, test for overlapping intervals; if
                ``False``, test for contiguous intervals.
        """
        for i in range(len(self.intervals)):
            for j in range(i + 1, len(self.intervals)):
                first = self.intervals[i]
                second = self.intervals[j]
                if test_overlap:
                    test = first.overlaps(second)
                else:
                    test = first.contiguous(second)
                if test:
                    return True
        return False

    # -------------------------------------------------------------------------
    # Simple descriptions
    # -------------------------------------------------------------------------

    def is_empty(self) -> bool:
        """
        Do we have no intervals?
        """
        return len(self.intervals) == 0

    def any_overlap(self) -> bool:
        """
        Do any of the intervals overlap?
        """
        return self._any_overlap_or_contiguous(test_overlap=True)

    def any_contiguous(self) -> bool:
        """
        Are any of the intervals contiguous?
        """
        return self._any_overlap_or_contiguous(test_overlap=False)

    # -------------------------------------------------------------------------
    # Start, end, range, duration
    # -------------------------------------------------------------------------

    def start_datetime(self) -> Optional[datetime.datetime]:
        """
        Returns the start date of the set of intervals, or ``None`` if empty.
        """
        if not self.intervals:
            return None
        return self.intervals[0].start
        # Internally sorted by start date, so this is always OK.

    def end_datetime(self) -> Optional[datetime.datetime]:
        """
        Returns the end date of the set of intervals, or ``None`` if empty.
        """
        if not self.intervals:
            return None
        return max([x.end for x in self.intervals])

    def start_date(self) -> Optional[datetime.date]:
        """
        Returns the start date of the set of intervals, or ``None`` if empty.
        """
        if not self.intervals:
            return None
        return self.start_datetime().date()

    def end_date(self) -> Optional[datetime.date]:
        """
        Returns the end date of the set of intervals, or ``None`` if empty.
        """
        if not self.intervals:
            return None
        return self.end_datetime().date()

    def extent(self) -> Optional[Interval]:
        """
        Returns an :class:`Interval` running from the earliest start of an
        interval in this list to the latest end. Returns ``None`` if we are
        empty.
        """
        if not self.intervals:
            return None
        return Interval(self.start_datetime(), self.end_datetime())

    def total_duration(self) -> datetime.timedelta:
        """
        Returns a ``datetime.timedelta`` object with the total sum of
        durations. If there is overlap, time will be double-counted, so beware!
        """
        total = datetime.timedelta()
        for interval in self.intervals:
            total += interval.duration()
        return total

    # -------------------------------------------------------------------------
    # Intervals and durations within our list
    # -------------------------------------------------------------------------

    def get_overlaps(self) -> "IntervalList":
        """
        Returns an :class:`IntervalList` containing intervals representing
        periods of overlap between intervals in this one.
        """
        overlaps = IntervalList()
        for i in range(len(self.intervals)):
            for j in range(i + 1, len(self.intervals)):
                first = self.intervals[i]
                second = self.intervals[j]
                ol = first.intersection(second)
                if ol is not None:
                    overlaps.add(ol)
        return overlaps

    def durations(self) -> List[datetime.timedelta]:
        """
        Returns a list of ``datetime.timedelta`` objects representing the
        durations of each interval in our list.
        """
        return [x.duration() for x in self.intervals]

    def longest_duration(self) -> Optional[datetime.timedelta]:
        """
        Returns the duration of the longest interval, or None if none.
        """
        if not self.intervals:
            return None
        return max(self.durations())

    def longest_interval(self) -> Optional[Interval]:
        """
        Returns the longest interval, or ``None`` if none.
        """
        longest_duration = self.longest_duration()
        for i in self.intervals:
            if i.duration() == longest_duration:
                return i
        return None

    def shortest_duration(self) -> Optional[datetime.timedelta]:
        """
        Returns the duration of the longest interval, or ``None`` if none.
        """
        if not self.intervals:
            return None
        return min(self.durations())

    def shortest_interval(self) -> Optional[Interval]:
        """
        Returns the shortest interval, or ``None`` if none.
        """
        shortest_duration = self.shortest_duration()
        for i in self.intervals:
            if i.duration() == shortest_duration:
                return i
        return None

    def first_interval_starting(self, start: datetime.datetime) -> \
            Optional[Interval]:
        """
        Returns our first interval that starts with the ``start`` parameter, or
        ``None``.
        """
        for i in self.intervals:
            if i.start == start:
                return i
        return None

    def first_interval_ending(self, end: datetime.datetime) \
            -> Optional[Interval]:
        """
        Returns our first interval that ends with the ``end`` parameter, or
        ``None``.
        """
        for i in self.intervals:
            if i.end == end:
                return i
        return None

    # -------------------------------------------------------------------------
    # Gaps and subsets
    # -------------------------------------------------------------------------

    def gaps(self) -> "IntervalList":
        """
        Returns all the gaps between intervals, as an :class:`IntervalList`.
        """
        if len(self.intervals) < 2:
            return IntervalList(None)
        gaps = []
        for i in range(len(self.intervals) - 1):
            gap = Interval(
                self.intervals[i].end,
                self.intervals[i + 1].start
            )
            gaps.append(gap)
        return IntervalList(gaps)

    def shortest_gap(self) -> Optional[Interval]:
        """
        Find the shortest gap between intervals, or ``None`` if none.
        """
        gaps = self.gaps()
        return gaps.shortest_interval()

    def shortest_gap_duration(self) -> Optional[datetime.timedelta]:
        """
        Find the duration of the shortest gap between intervals, or ``None`` if
        none.
        """
        gaps = self.gaps()
        return gaps.shortest_duration()

    def subset(self, interval: Interval,
               flexibility: int = 2) -> "IntervalList":
        """
        Returns an IntervalList that's a subset of this one, only containing
        intervals that meet the "interval" parameter criterion. What "meet"
        means is defined by the ``flexibility`` parameter.

        ``flexibility == 0``: permits only wholly contained intervals:

        .. code-block:: none

            interval:
                        I----------------I

            intervals in self that will/won't be returned:

                N---N  N---N   Y---Y   N---N   N---N
                    N---N                N---N

        ``flexibility == 1``: permits overlapping intervals as well:

        .. code-block:: none

                        I----------------I

                N---N  Y---Y   Y---Y   Y---Y   N---N
                    N---N                N---N

        ``flexibility == 2``: permits adjoining intervals as well:

        .. code-block:: none

                        I----------------I

                N---N  Y---Y   Y---Y   Y---Y   N---N
                    Y---Y                Y---Y
        """
        if flexibility not in [0, 1, 2]:
            raise ValueError("subset: bad flexibility value")
        permitted = []
        for i in self.intervals:
            if flexibility == 0:
                ok = i.start > interval.start and i.end < interval.end
            elif flexibility == 1:
                ok = i.end > interval.start and i.start < interval.end
            else:
                ok = i.end >= interval.start and i.start <= interval.end
            if ok:
                permitted.append(i)
        return IntervalList(permitted)

    def gap_subset(self, interval: Interval,
                   flexibility: int = 2) -> "IntervalList":
        """
        Returns an IntervalList that's a subset of this one, only containing
        *gaps* between intervals that meet the interval criterion.

        See :meth:`subset` for the meaning of parameters.
        """
        return self.gaps().subset(interval, flexibility)

    # -------------------------------------------------------------------------
    # Descriptions relating to the working week (for rota work)
    # -------------------------------------------------------------------------

    def n_weekends(self) -> int:
        """
        Returns the number of weekends that the intervals collectively touch
        (where "touching a weekend" means "including time on a Saturday or a
        Sunday").
        """
        saturdays = set()
        for interval in self.intervals:
            saturdays.update(interval.saturdays_of_weekends())
        return len(saturdays)

    def duration_outside_nwh(
            self,
            starttime: datetime.time = datetime.time(NORMAL_DAY_START_H),
            endtime: datetime.time = datetime.time(NORMAL_DAY_END_H)) \
            -> datetime.timedelta:
        """
        Returns the total duration outside normal working hours, i.e.
        evenings/nights, weekends (and Bank Holidays).
        """
        total = datetime.timedelta()
        for interval in self.intervals:
            total += interval.duration_outside_nwh(starttime, endtime)
        return total

    def max_consecutive_days(self) -> Optional[Tuple[int, Interval]]:
        """
        The length of the longest sequence of days in which all days include
        an interval.

        Returns:
             tuple:
                ``(longest_length, longest_interval)`` where
                ``longest_interval`` is a :class:`Interval` containing the
                start and end date of the longest span -- or ``None`` if we
                contain no intervals.
        """
        if len(self.intervals) == 0:
            return None
        startdate = self.start_date()
        enddate = self.end_date()
        seq = ''
        ndays = (enddate - startdate).days + 1
        for i in range(ndays):
            date = startdate + datetime.timedelta(days=i)
            wholeday = Interval.wholeday(date)
            if any([x.overlaps(wholeday) for x in self.intervals]):
                seq += '+'
            else:
                seq += ' '
        # noinspection PyTypeChecker
        longest = max(seq.split(), key=len)
        longest_len = len(longest)
        longest_idx = seq.index(longest)
        longest_interval = Interval.dayspan(
            startdate + datetime.timedelta(days=longest_idx),
            startdate + datetime.timedelta(days=longest_idx + longest_len)
        )
        return longest_len, longest_interval

    def _sufficient_gaps(self,
                         startdate: datetime.date,
                         enddate: datetime.date,
                         requiredgaps: List[datetime.timedelta],
                         flexibility: int) -> Tuple[bool, Optional[Interval]]:
        """
        Are there sufficient gaps (specified by ``requiredgaps``) in the date
        range specified? This is a worker function for :meth:`sufficient_gaps`.
        """
        requiredgaps = list(requiredgaps)  # make a copy
        interval = Interval.dayspan(startdate, enddate, include_end=True)
        # log.debug(">>> _sufficient_gaps")
        gaps = self.gap_subset(interval, flexibility)
        gapdurations = gaps.durations()
        gaplist = gaps.list()
        gapdurations.sort(reverse=True)  # longest gap first
        requiredgaps.sort(reverse=True)  # longest gap first
        # log.debug("... gaps = {}".format(gaps))
        # log.debug("... gapdurations = {}".format(gapdurations))
        # log.debug("... requiredgaps = {}".format(requiredgaps))
        while requiredgaps:
            # log.debug("... processing gap")
            if not gapdurations:
                # log.debug("<<< no gaps left")
                return False, None
            if gapdurations[0] < requiredgaps[0]:
                # log.debug("<<< longest gap is too short")
                return False, self.first_interval_ending(gaplist[0].start)
            gapdurations.pop(0)
            requiredgaps.pop(0)
            gaplist.pop(0)
            # ... keeps gaplist and gapdurations mapped to each other
        # log.debug("<<< success")
        return True, None

    def sufficient_gaps(self,
                        every_n_days: int,
                        requiredgaps: List[datetime.timedelta],
                        flexibility: int = 2) \
            -> Tuple[bool, Optional[Interval]]:
        """
        Are gaps present sufficiently often?
        For example:

        .. code-block:: python

            every_n_days=21
            requiredgaps=[
                datetime.timedelta(hours=62),
                datetime.timedelta(hours=48),
            ]

        ... means "is there at least one 62-hour gap and one (separate) 48-hour
        gap in every possible 21-day sequence within the IntervalList?

        - If ``flexibility == 0``: gaps must be WHOLLY WITHIN the interval.

        - If ``flexibility == 1``: gaps may OVERLAP the edges of the interval.

        - If ``flexibility == 2``: gaps may ABUT the edges of the interval.

        Returns ``(True, None)`` or ``(False, first_failure_interval)``.
        """
        if len(self.intervals) < 2:
            return False, None
        startdate = self.start_date()
        enddate = self.end_date()
        ndays = (enddate - startdate).days + 1
        if ndays <= every_n_days:
            # Our interval is too short, or just right
            return self._sufficient_gaps(startdate, enddate, requiredgaps,
                                         flexibility)
        for i in range(ndays - every_n_days):
            j = i + every_n_days
            a = startdate + datetime.timedelta(days=i)
            b = startdate + datetime.timedelta(days=j)
            sufficient, ffi = self._sufficient_gaps(a, b, requiredgaps,
                                                    flexibility)
            if not sufficient:
                return False, ffi
        return True, None

    # -------------------------------------------------------------------------
    # Cumulative time calculations
    # -------------------------------------------------------------------------

    def cumulative_time_to(self,
                           when: datetime.datetime) -> datetime.timedelta:
        """
        Returns the cumulative time contained in our intervals up to the
        specified time point.
        """
        assert self.no_overlap, self._ONLY_FOR_NO_INTERVAL
        cumulative = datetime.timedelta()
        for interval in self.intervals:
            if interval.start >= when:
                break
            elif interval.end <= when:
                # complete interval precedes "when"
                cumulative += interval.duration()
            else:  # start < when < end
                cumulative += when - interval.start
        return cumulative

    def cumulative_gaps_to(self,
                           when: datetime.datetime) -> datetime.timedelta:
        """
        Return the cumulative time within our gaps, up to ``when``.
        """
        gaps = self.gaps()
        return gaps.cumulative_time_to(when)

    def time_afterwards_preceding(
            self, when: datetime.datetime) -> Optional[datetime.timedelta]:
        """
        Returns the time after our last interval, but before ``when``.
        If ``self`` is an empty list, returns ``None``.
        """
        if self.is_empty():
            return None
        end_time = self.end_datetime()
        if when <= end_time:
            return datetime.timedelta()
        else:
            return when - end_time

    def cumulative_before_during_after(self,
                                       start: datetime.datetime,
                                       when: datetime.datetime) -> \
            Tuple[datetime.timedelta,
                  datetime.timedelta,
                  datetime.timedelta]:
        """
        For a given time, ``when``, returns the cumulative time
        
        - after ``start`` but before ``self`` begins, prior to ``when``;
        - after ``start`` and during intervals represented by ``self``, prior
          to ``when``;
        - after ``start`` and after at least one interval represented by
          ``self`` has finished, and not within any intervals represented by
          ``self``, and prior to ``when``.
          
        Args:
            start: the start time of interest (e.g. before ``self`` begins)
            when: the time of interest
            
        Returns:
            tuple: ``before, during, after``

        Illustration
        
        .. code-block:: none
        
        
            start:      S
            self:           X---X       X---X       X---X       X---X
            
            when:                                           W
            
            before:     ----
            during:         -----       -----       -----
            after:               -------     -------     ----

        """
        assert self.no_overlap, (
            "Only implemented for IntervalList objects with no_overlap == True"
        )
        no_time = datetime.timedelta()
        earliest_interval_start = self.start_datetime()

        # Easy special cases
        if when <= start:
            return no_time, no_time, no_time
        if self.is_empty() or when <= earliest_interval_start:
            return when - start, no_time, no_time

        # Now we can guarantee:
        # - "self" is a non-empty list
        # - start < when
        # - earliest_interval_start < when

        # Before
        if earliest_interval_start < start:
            before = no_time
        else:
            before = earliest_interval_start - start

        # During
        during = self.cumulative_time_to(when)

        after = (
            self.cumulative_gaps_to(when) +
            self.time_afterwards_preceding(when)
        )

        return before, during, after


# =============================================================================
# Unit testing
# =============================================================================

class TestInterval(unittest.TestCase):
    """
    Unit tests.
    """
    def test_interval(self) -> None:
        a = datetime.datetime(2015, 1, 1)
        log.debug(f"a = {a!r}")
        b = datetime.datetime(2015, 1, 6)
        log.debug(f"b = {b!r}")
        i = Interval(a, b)
        log.debug(f"i = {i!r}")
        j = i + datetime.timedelta(hours=3)
        log.debug(f"j = {j!r}")
        cut = i.cut(datetime.datetime(2015, 1, 3))
        log.debug(f"cut = {cut!r}")


# =============================================================================
# main
# =============================================================================

if __name__ == "__main__":
    main_only_quicksetup_rootlogger(level=logging.DEBUG)
    log.info("Running unit tests")
    unittest.main(argv=[sys.argv[0]])
    sys.exit(0)
