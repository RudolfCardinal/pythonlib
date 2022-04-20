#!/usr/bin/env python
# cardinal_pythonlib/psychiatry/tests/timeline_tests.py

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

**Unit tests.**

"""

import datetime
import logging
from typing import List
import unittest

from numpy import array
from pandas import DataFrame

from cardinal_pythonlib.logs import BraceStyleAdapter
from cardinal_pythonlib.psychiatry.timeline import (
    cumulative_time_on_drug,
    drug_timelines,
    DTYPE_DATETIME,
    DTYPE_STRING,
)

log = BraceStyleAdapter(logging.getLogger(__name__))

DEFAULT_PATIENT_COLNAME = "patient_id"
DEFAULT_DRUG_EVENT_DATETIME_COLNAME = "drug_event_datetime"
DEFAULT_START_DATETIME_COLNAME = "start"
DEFAULT_QUERY_DATETIME_COLNAME = "when"


# =============================================================================
# Unit testing
# =============================================================================


class TestTimeline(unittest.TestCase):
    """
    Unit tests.
    """

    DATEFORMAT = "%Y-%m-%d"
    DATETIMEFORMAT = "%Y-%m-%d %H:%M"

    DRUG_EVENT_TIME = " 00:00"  # " 09:00"
    QUERY_EVENT_TIME = " 00:00"  # " 12:00"

    @classmethod
    def dateseq(
        cls, first: str, last: str, time_suffix: str = ""
    ) -> List[datetime.datetime]:
        fmt = cls.DATETIMEFORMAT if time_suffix else cls.DATEFORMAT
        if time_suffix:
            first += time_suffix
            last += time_suffix
        dfirst = datetime.datetime.strptime(first, fmt)
        dlast = datetime.datetime.strptime(last, fmt)
        assert dfirst <= dlast
        dates = []  # type: List[datetime.datetime]
        d = dfirst
        while d <= dlast:
            dates.append(d)
            d += datetime.timedelta(days=1)
        return dates

    def test_timeline(self) -> None:
        event_lasts_for = datetime.timedelta(weeks=4)
        # event_lasts_for = datetime.timedelta(days=3)
        log.debug("event_lasts_for: {!r}", event_lasts_for)

        alice = "Alice"
        drug_events_arr = array(
            [
                # Alice
                (alice, "2018-01-05" + self.DRUG_EVENT_TIME),
                (alice, "2018-01-20" + self.DRUG_EVENT_TIME),
                (alice, "2018-04-01" + self.DRUG_EVENT_TIME),
            ],
            dtype=[
                (DEFAULT_PATIENT_COLNAME, DTYPE_STRING),
                (DEFAULT_DRUG_EVENT_DATETIME_COLNAME, DTYPE_DATETIME),
            ],
        )
        drug_events_df = DataFrame.from_records(drug_events_arr)
        log.debug("drug_events_df:\n{!r}", drug_events_df)

        start = datetime.datetime.strptime(
            "2017-01-01" + self.DRUG_EVENT_TIME, self.DATETIMEFORMAT
        )
        log.debug("start: {!r}", start)

        qdata_rows = []
        for dt in self.dateseq(
            "2018-01-01", "2018-05-30", time_suffix=self.QUERY_EVENT_TIME
        ):
            qdata_rows.append((alice, start, dt))
        query_times_arr = array(
            qdata_rows,
            dtype=[
                (DEFAULT_PATIENT_COLNAME, DTYPE_STRING),
                (DEFAULT_START_DATETIME_COLNAME, DTYPE_DATETIME),
                (DEFAULT_QUERY_DATETIME_COLNAME, DTYPE_DATETIME),
            ],
        )
        query_times_df = DataFrame.from_records(query_times_arr)
        log.debug("query_times_df:\n{!r}", query_times_df)

        timelines = drug_timelines(
            drug_events_df=drug_events_df,
            event_lasts_for=event_lasts_for,
            patient_colname=DEFAULT_PATIENT_COLNAME,
            event_datetime_colname=DEFAULT_DRUG_EVENT_DATETIME_COLNAME,
        )
        log.debug("timelines: {!r}", timelines)

        cumulative = cumulative_time_on_drug(
            drug_events_df=drug_events_df,
            event_lasts_for_timedelta=event_lasts_for,
            query_times_df=query_times_df,
            patient_colname=DEFAULT_PATIENT_COLNAME,
            event_datetime_colname=DEFAULT_DRUG_EVENT_DATETIME_COLNAME,
            start_colname=DEFAULT_START_DATETIME_COLNAME,
            when_colname=DEFAULT_QUERY_DATETIME_COLNAME,
        )
        log.debug("cumulative:\n{}", cumulative)
