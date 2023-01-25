#!/usr/bin/env python
# cardinal_pythonlib/tests/datetimefunc_tests.py

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

**Unit tests.**

"""

import datetime
import logging
import unittest

import isodate.isoerror
from isodate.isoduration import Duration as IsodateDuration
from pendulum import Date, DateTime, Duration

from cardinal_pythonlib.datetimefunc import (
    coerce_to_date,
    coerce_to_datetime,
    coerce_to_pendulum,
    duration_from_iso,
    duration_to_iso,
    get_pendulum_duration_nonyear_nonmonth_seconds,
    pendulum_duration_from_isodate_duration,
    pendulum_duration_from_timedelta,
    pendulum_to_datetime_stripping_tz,
)

log = logging.getLogger(__name__)


# =============================================================================
# Unit testing
# =============================================================================


class TestCoerceToPendulum(unittest.TestCase):
    def test_returns_none_if_falsey(self) -> None:
        self.assertIsNone(coerce_to_pendulum(""))

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
            2020,
            6,
            15,
            hour=15,
            minute=42,
            tzinfo=datetime.timezone(utc_offset),
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
            datetime_out.utcoffset(), datetime.timedelta(hours=5, minutes=30)
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
            (
                f"Failed conversion {iso_duration!r} "
                f"-> {d1!r} -> {i2!r} -> {d2!r}",
            ),
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

    def _assert_iso_microsecond_fails(
        self, iso_duration: str, correct_microseconds: int
    ) -> None:
        """
        For conversions that do NOT work.
        """
        d1 = duration_from_iso(iso_duration)
        self.assertNotEqual(
            d1.microseconds,
            correct_microseconds,
            f"Unexpected microsecond success: {iso_duration!r} -> {d1!r}",
        )

    def assert_isodateduration_eq_pendulumduration(
        self, i: isodate.Duration, p: Duration
    ) -> None:
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
            f"{p!r} -> {end_p!r}.",
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
            len(i9longest), longest_feasible_iso_duration_no_year_month
        )

        i11longest_with_us = "-P0Y0MT1000000000.000009S"
        self._assert_iso_converts(i11longest_with_us)  # microseconds correct

        i12toolong_rounds_us = "-P0Y0MT10000000000.000009S"
        self._assert_iso_microsecond_fails(
            i12toolong_rounds_us, correct_microseconds=9
        )
        self._assert_iso_converts(i12toolong_rounds_us)

        i13toolong_drops_us = "-P0Y0MT10000000000000.000009S"
        self._assert_iso_microsecond_fails(
            i13toolong_drops_us, correct_microseconds=9
        )
        # ... drops microseconds (within datetime.timedelta)
        self._assert_iso_converts(i13toolong_drops_us)

        i14toolong_parse_fails = "-P0Y0MT100000000000000.000009S"
        self._assert_iso_overflows(i14toolong_parse_fails)  # too many days

        longest_without_ym = duration_to_iso(
            duration_from_iso(i11longest_with_us), permit_years_months=False
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
            f"{td!r}.total_seconds() != {pd!r}.total_seconds()",
        )

    def test_pendulum_duration_from_timedelta(self) -> None:
        self._check_td_to_pd(
            datetime.timedelta(days=5, hours=3, minutes=2, microseconds=5)
        )
        self._check_td_to_pd(datetime.timedelta(microseconds=5010293989234))
        self._check_td_to_pd(datetime.timedelta(days=5000))

    # -------------------------------------------------------------------------
    # isodate.isoduration.Duration versus pendulum.Duration
    # -------------------------------------------------------------------------

    def test_isodate_pendulum_duration_equivalence(self) -> None:
        """
        Check that our IsodateDuration and Duration objects are being handled
        equivalently.
        """
        self.assert_isodateduration_eq_pendulumduration(
            IsodateDuration(years=1, seconds=1), Duration(years=1, seconds=1)
        )

    def _check_id_to_pd(self, isodur: IsodateDuration) -> None:
        pendur = pendulum_duration_from_isodate_duration(isodur)
        self.assertEqual(
            isodur.years,
            pendur.years,
            f"Year mismatch: {isodur!r} -> {isodur.years!r} != "
            f"{pendur!r} -> {pendur.years!r}",
        )
        self.assertEqual(
            isodur.months,
            pendur.months,
            f"Month mismatch: {isodur!r} -> {isodur.months!r} != "
            f"{pendur!r} -> {pendur.months!r}",
        )
        id_non_ym_seconds = isodur.tdelta.total_seconds()
        pd_non_ym_seconds = get_pendulum_duration_nonyear_nonmonth_seconds(
            pendur
        )
        self.assertEqual(
            id_non_ym_seconds,
            pd_non_ym_seconds,
            f"Seconds mismatch (ignoring year/month component): "
            f"{isodur!r} -> {id_non_ym_seconds} != "
            f"{pendur!r} -> {pd_non_ym_seconds!r}",
        )

    def test_pendulum_duration_from_isodate_duration(self) -> None:
        self._check_id_to_pd(
            IsodateDuration(days=5, hours=3, minutes=2, microseconds=5)
        )
        self._check_id_to_pd(IsodateDuration(microseconds=5010293989234))
        self._check_id_to_pd(IsodateDuration(days=5000))
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
            basedate1 + Duration(years=1), DateTime(year=2001, month=1, day=1)
        )
        self.assertEqual(
            basedate1 + Duration(months=1), DateTime(year=2000, month=2, day=1)
        )
        basedate2 = DateTime(
            year=2004, month=2, day=1
        )  # 2004-02-01; leap year
        self.assertEqual(
            basedate2 + Duration(years=1), DateTime(year=2005, month=2, day=1)
        )
        self.assertEqual(
            basedate2 + Duration(months=1), DateTime(year=2004, month=3, day=1)
        )
        self.assertEqual(
            basedate2 + Duration(months=1, days=1),
            DateTime(year=2004, month=3, day=2),
        )


class TestCoerceToDateTime(unittest.TestCase):
    def test_coerce_to_datetime(self) -> None:
        # No timezone:
        d1 = datetime.datetime(2022, 2, 28, 1, 0, 0)  # 1 a.m. on 28 Feb
        # With timezone:
        d2 = datetime.datetime(
            # 11pm on 27 Feb in New York, which is 4am on 28 Feb in UTC.
            2022,
            2,
            27,
            23,
            0,
            0,
            tzinfo=datetime.timezone(datetime.timedelta(hours=-5)),
        )
        correct_from_to_tuples = (
            # No timezone:
            # ... from Pendulum DateTime:
            (DateTime(2022, 2, 28, 1, 0, 0), d1),
            # ... from string:
            ("2022-02-28T01:00", d1),
            # With timezone:
            # ... from Pendulum DateTime:
            (
                DateTime(
                    2022,
                    2,
                    27,
                    23,
                    0,
                    0,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=-5)),
                ),
                d2,
            ),
            # ... from string:
            ("2022-02-27T23:00-05:00", d2),
        )
        wrong_from_to_tuples = (
            # Some things that should fail:
            ("2022-02-28T01:00-05:00", d1),
            ("2022-02-28T01:00+05:00", d1),
        )
        for from_, to_ in correct_from_to_tuples:
            self.assertEqual(
                coerce_to_datetime(from_),
                to_,
                f"Should convert {from_!r} -> {to_!r}",
            )
        for from_, to_ in wrong_from_to_tuples:
            self.assertNotEqual(
                coerce_to_datetime(from_),
                to_,
                f"Should NOT convert {from_!r} -> {to_!r}",
            )


class TestCoerceToDate(unittest.TestCase):
    # Indirectly tests coerce_to_pendulum_date too.
    def test_coerce_to_date(self) -> None:
        # Simple:
        d1 = datetime.date(2022, 2, 28)
        correct_from_to_tuples = (
            # ... from Pendulum Date:
            (Date(2022, 2, 28), d1),
            # ... from Pendulum DateTime:
            (DateTime(2022, 2, 28, 23, 59, 59), d1),
            (
                DateTime(
                    2022,
                    2,
                    28,
                    23,
                    59,
                    59,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=-5)),
                ),
                d1,
            ),
            # ... from string:
            ("2022-02-28", d1),
            ("2022-02-28T01:00", d1),
            ("2022-02-28T01:00+05:00", d1),
            ("2022-02-28T01:00-05:00", d1),
        )
        for from_, to_ in correct_from_to_tuples:
            self.assertEqual(coerce_to_date(from_), to_)

        # to_utc:
        self.assertEqual(
            coerce_to_date("2022-02-27T23:00-05:00", to_utc=False),
            datetime.date(2022, 2, 27),
        )
        self.assertEqual(
            coerce_to_date("2022-02-27T23:00-05:00", to_utc=True),
            datetime.date(2022, 2, 28),
        )
