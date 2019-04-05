#!/usr/bin/env python
# cardinal_pythonlib/psychiatry/timeline.py

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

Timeline calculations.
Primarily for a lithium/renal function project, Apr 2019.
Code is in DRAFT.

Usage from R:

.. code-block:: r

    # -------------------------------------------------------------------------
    # Load libraries
    # -------------------------------------------------------------------------

    RUN_ONCE_ONLY <- '
        library(devtools)
        devtools::install_github("rstudio/reticulate")  # get latest version
    '
    library(data.table)
    library(reticulate)

    # -------------------------------------------------------------------------
    # Set up reticulate
    # -------------------------------------------------------------------------

    VENV <- "~/dev/venvs/cardinal_pythonlib"  # or your preferred virtualenv
    PYTHON_EXECUTABLE <- ifelse(
        .Platform$OS.type == "windows",
        file.path(VENV, "Scripts", "python.exe"),  # Windows
        file.path(VENV, "bin", "python")  # Linux
    )
    reticulate::use_python(PYTHON_EXECUTABLE, required=TRUE)

    # -------------------------------------------------------------------------
    # Import Python modules
    # -------------------------------------------------------------------------

    cpl_version <- reticulate::import("cardinal_pythonlib.version")
    cpl_version$assert_version_eq("1.0.50")
    cpl_logs <- reticulate::import("cardinal_pythonlib.logs")
    cpl_logs$main_only_quicksetup_rootlogger()

    cpl_timeline <- reticulate::import("cardinal_pythonlib.psychiatry.timeline")

    # -------------------------------------------------------------------------
    # Do something
    # -------------------------------------------------------------------------

    testdata_drug_events <- data.table(
        patient_id=c(
            rep("Alice", 3), 
            rep("Bob", 3)
        ),
        drug_event_datetime=as.Date(c(
            # Alice
            "2018-01-05",
            "2018-01-20",
            "2018-04-01",
            # Bob
            "2018-06-05",
            "2018-08-20",
            "2018-10-01"
        ))
    )
    testdata_query_times <- data.table(
        patient_id=c(
            rep("Alice", 3),
            rep("Bob", 3)
        ),
        start=as.Date(c(
            # Alice
            rep("2017-01-01", 3),
            # Bob
            rep("2015-01-01", 3)
        )),
        when=as.Date(c(
            # Alice
            "2018-01-01",
            "2018-01-10",
            "2018-02-01",
            # Bob
            "2018-01-01",
            "2018-09-10",
            "2019-02-01"
        ))
    )
    testresult <- data.table(cpl_timeline$cumulative_time_on_drug(
        drug_events_df=testdata_drug_events,
        event_lasts_for_quantity=3,
        event_lasts_for_units="days",
        query_times_df=testdata_query_times,
        patient_colname="patient_id",
        event_datetime_colname="drug_event_datetime",
        start_colname="start",
        when_colname="when",
        debug=TRUE
    ))
    print(testresult)

The result should be:

.. code-block:: none

    > print(testdata_drug_events)

       patient_id drug_event_datetime
    1:      Alice          2018-01-05
    2:      Alice          2018-01-20
    3:      Alice          2018-04-01
    4:        Bob          2018-06-05
    5:        Bob          2018-08-20
    6:        Bob          2018-10-01

    > print(testdata_query_times)

       patient_id      start       when
    1:      Alice 2017-01-01 2018-01-01
    2:      Alice 2017-01-01 2018-01-10
    3:      Alice 2017-01-01 2018-02-01
    4:        Bob 2015-01-01 2018-01-01
    5:        Bob 2015-01-01 2018-09-10
    6:        Bob 2015-01-01 2019-02-01

    > print(testresult)

       patient_id      start          t before_days during_days after_days
    1:      Alice 2017-01-01 2018-01-01         365           0          0
    2:      Alice 2017-01-01 2018-01-10         369           3          2
    3:      Alice 2017-01-01 2018-02-01         369           6         21
    4:        Bob 2015-01-01 2018-01-01        1096           0          0
    5:        Bob 2015-01-01 2018-09-10        1251           6         91
    6:        Bob 2015-01-01 2019-02-01        1251           9        232

However, there is a ``reticulate`` bug that can cause problems, by corrupting
dates passed from R to Python:

.. code-block:: r

    # PROBLEM on 2018-04-05, with reticulate 1.11.1:
    # - the R data.table is fine
    # - all the dates become the same date when it's seen by Python (the value
    #   of the first row in each date column)
    # - when used without R, the Python code is fine
    # - therefore, a problem with reticulate converting data for Python
    # - same with data.frame() as with data.table()
    # - same with as.Date.POSIXct() and as.Date.POSIXlt() as with as.Date()

    # Further test:

    cpl_rfunc <- reticulate::import("cardinal_pythonlib.psychiatry.rfunc")
    cat(cpl_rfunc$get_python_repr(testdata_drug_events))
    cat(cpl_rfunc$get_python_repr_of_type(testdata_drug_events))
    print(testdata_drug_events)
    print(reticulate::r_to_py(testdata_drug_events))

    # Minimum reproducible example:

    library(reticulate)
    testdata_drug_events <- data.frame(
        patient_id=c(
            rep("Alice", 3),
            rep("Bob", 3)
        ),
        drug_event_datetime=as.Date(c(
            # Alice
            "2018-01-05",
            "2018-01-20",
            "2018-04-01",
            # Bob
            "2018-06-05",
            "2018-08-20",
            "2018-10-01"
        ))
    )
    print(testdata_drug_events)
    print(reticulate::r_to_py(testdata_drug_events))

    # The R data is:
    #
    #       patient_id drug_event_datetime
    #     1      Alice          2018-01-05
    #     2      Alice          2018-01-20
    #     3      Alice          2018-04-01
    #     4        Bob          2018-06-05
    #     5        Bob          2018-08-20
    #     6        Bob          2018-10-01
    #
    # Output from reticulate::r_to_py() in the buggy version is:
    #
    #       patient_id drug_event_datetime
    #     0      Alice          2018-01-05
    #     1      Alice          2018-01-05
    #     2      Alice          2018-01-05
    #     3        Bob          2018-01-05
    #     4        Bob          2018-01-05
    #     5        Bob          2018-01-05
    #
    # Known bug: https://github.com/rstudio/reticulate/issues/454
    #
    # Use remove.packages() then reinstall from github as above, giving
    # reticulate_1.11.1-9000 [see sessionInfo()]...
    # ... yes, that fixes it.

"""

from collections import defaultdict
import datetime
import logging
import sys
from typing import Any, Dict, List
import unittest

from numpy import array
from pandas import DataFrame

from cardinal_pythonlib.interval import Interval, IntervalList
from cardinal_pythonlib.logs import (
    BraceStyleAdapter,
    main_only_quicksetup_rootlogger,
)

log = BraceStyleAdapter(logging.getLogger(__name__))

DEFAULT_PATIENT_COLNAME = "patient_id"
DEFAULT_DRUG_EVENT_DATETIME_COLNAME = "drug_event_datetime"
DEFAULT_START_DATETIME_COLNAME = "start"
DEFAULT_QUERY_DATETIME_COLNAME = "when"


def drug_timelines(
        drug_events_df: DataFrame,
        event_lasts_for: datetime.timedelta,
        patient_colname: str = DEFAULT_PATIENT_COLNAME,
        event_datetime_colname: str = DEFAULT_DRUG_EVENT_DATETIME_COLNAME) \
        -> Dict[Any, IntervalList]:
    """
    Takes a set of drug event start times (one or more per patient), plus a
    fixed time that each event is presumed to last for, and returns an
    :class:`IntervalList` for each patient representing the set of events
    (which may overlap, in which case they will be amalgamated).

    Args:
        drug_events_df:
            pandas :class:`DataFrame` containing the event data
        event_lasts_for:
            when an event occurs, how long is it assumed to last for? For
            example, if a prescription of lithium occurs on 2001-01-01, how
            long is the patient presumed to be taking lithium as a consequence
            (e.g. 1 day? 28 days? 6 months?)
        patient_colname:
            name of the column in ``drug_events_df`` containing the patient ID
        event_datetime_colname:
            name of the column in ``drug_events_df`` containing the date/time
            of each event

    Returns:
        dict: mapping patient ID to a :class:`IntervalList` object indicating
        the amalgamated intervals from the events

    """
    sourcecolnum_pt = drug_events_df.columns.get_loc(patient_colname)
    sourcecolnum_when = drug_events_df.columns.get_loc(event_datetime_colname)
    timelines = defaultdict(IntervalList)
    nrows = len(drug_events_df)
    for rowidx in range(nrows):
        patient_id = drug_events_df.iat[rowidx, sourcecolnum_pt]
        event_when = drug_events_df.iat[rowidx, sourcecolnum_when]
        interval = Interval(event_when, event_when + event_lasts_for)
        ivlist = timelines[patient_id]  # will create if unknown
        ivlist.add(interval)
    return timelines


DTYPE_STRING = "<U255"
# ... see treatment_resistant_depression.py
DTYPE_DATETIME = "datetime64[s]"
# ... https://docs.scipy.org/doc/numpy/reference/arrays.datetime.html
DTYPE_FLOAT = "Float64"
# ... https://docs.scipy.org/doc/numpy/reference/arrays.dtypes.html
DTYPE_TIMEDELTA = "timedelta64"

RCN_PATIENT_ID = "patient_id"  # RCN: "result column name"
RCN_START = "start"
RCN_TIME = "t"
RCN_BEFORE_TIMEDELTA = "before_timedelta"
RCN_DURING_TIMEDELTA = "during_timedelta"
RCN_AFTER_TIMEDELTA = "after_timedelta"
RCN_BEFORE_DAYS = "before_days"
RCN_DURING_DAYS = "during_days"
RCN_AFTER_DAYS = "after_days"


def cumulative_time_on_drug(
        drug_events_df: DataFrame,
        query_times_df: DataFrame,
        event_lasts_for_timedelta: datetime.timedelta = None,
        event_lasts_for_quantity: float = None,
        event_lasts_for_units: str = None,
        patient_colname: str = DEFAULT_PATIENT_COLNAME,
        event_datetime_colname: str = DEFAULT_DRUG_EVENT_DATETIME_COLNAME,
        start_colname: str = DEFAULT_START_DATETIME_COLNAME,
        when_colname: str = DEFAULT_QUERY_DATETIME_COLNAME,
        include_timedelta_in_output: bool = False,
        debug: bool = False) \
        -> DataFrame:
    """

    Args:
        drug_events_df:
            pandas :class:`DataFrame` containing the event data, with columns
            named according to ``patient_colname``, ``event_datetime_colname``
        event_lasts_for_timedelta:
            when an event occurs, how long is it assumed to last for? For
            example, if a prescription of lithium occurs on 2001-01-01, how
            long is the patient presumed to be taking lithium as a consequence
            (e.g. 1 day? 28 days? 6 months?)
        event_lasts_for_quantity:
            as an alternative to ``event_lasts_for_timedelta``, particularly if
            you are calling from R to Python via ``reticulate`` (which doesn't
            convert R ``as.difftime()`` to Python ``datetime.timedelta``), you
            can specify ``event_lasts_for_quantity``, a number and
            ``event_lasts_for_units`` (q.v.).
        event_lasts_for_units:
            specify the units for ``event_lasts_for_quantity`` (q.v.), if used;
            e.g. ``"days"``. The string value must be the name of an argument
            to the Python ``datetime.timedelta`` constructor.
        query_times_df:
            times to query for, with columns named according to
            ``patient_colname``, ``start_colname``, and ``when_colname``
        patient_colname:
            name of the column in ``drug_events_df`` and ``query_time_df``
            containing the patient ID
        event_datetime_colname:
            name of the column in ``drug_events_df`` containing the date/time
            of each event
        start_colname:
            name of the column in ``query_time_df`` containing the date/time
            representing the overall start time for the relevant patient (from
            which cumulative times are calculated)
        when_colname:
            name of the column in ``query_time_df`` containing date/time
            values at which to query
        include_timedelta_in_output:
            include ``datetime.timedelta`` values in the output? The default is
            ``False`` as this isn't supported by R/``reticulate``.
        debug:
            print debugging information to the log?

    Returns:
        :class:`DataFrame` with the requested data

    """
    if event_lasts_for_timedelta is None:
        assert event_lasts_for_quantity and event_lasts_for_units
        timedelta_dict = {event_lasts_for_units: event_lasts_for_quantity}
        event_lasts_for_timedelta = datetime.timedelta(**timedelta_dict)
    if debug:
        log.critical("drug_events_df:\n{!r}", drug_events_df)
        log.critical("event_lasts_for:\n{!r}", event_lasts_for_timedelta)
        log.critical("query_times_df:\n{!r}", query_times_df)
    timelines = drug_timelines(
        drug_events_df=drug_events_df,
        event_lasts_for=event_lasts_for_timedelta,
        patient_colname=patient_colname,
        event_datetime_colname=event_datetime_colname,
    )
    query_nrow = len(query_times_df)
    ct_coldefs = [  # column definitions:
        (RCN_PATIENT_ID, DTYPE_STRING),
        (RCN_START, DTYPE_DATETIME),
        (RCN_TIME, DTYPE_DATETIME),
        (RCN_BEFORE_DAYS, DTYPE_FLOAT),
        (RCN_DURING_DAYS, DTYPE_FLOAT),
        (RCN_AFTER_DAYS, DTYPE_FLOAT),
    ]
    if include_timedelta_in_output:
        ct_coldefs.extend([
            (RCN_BEFORE_TIMEDELTA, DTYPE_TIMEDELTA),
            (RCN_DURING_TIMEDELTA, DTYPE_TIMEDELTA),
            (RCN_AFTER_TIMEDELTA, DTYPE_TIMEDELTA),
        ])
    ct_arr = array([None] * query_nrow, dtype=ct_coldefs)
    # log.debug("ct_arr:\n{!r}", ct_arr)
    cumulative_times = DataFrame(ct_arr, index=list(range(query_nrow)))
    # log.debug("cumulative_times:\n{!r}", cumulative_times)
    # So we can use the fast "iat" function.
    sourcecolnum_pt = query_times_df.columns.get_loc(patient_colname)
    sourcecolnum_start = query_times_df.columns.get_loc(start_colname)
    sourcecolnum_when = query_times_df.columns.get_loc(when_colname)
    dest_colnum_pt = cumulative_times.columns.get_loc(RCN_PATIENT_ID)
    dest_colnum_start = cumulative_times.columns.get_loc(RCN_START)
    dest_colnum_t = cumulative_times.columns.get_loc(RCN_TIME)
    dest_colnum_before_days = cumulative_times.columns.get_loc(RCN_BEFORE_DAYS)
    dest_colnum_during_days = cumulative_times.columns.get_loc(RCN_DURING_DAYS)
    dest_colnum_after_days = cumulative_times.columns.get_loc(RCN_AFTER_DAYS)
    if include_timedelta_in_output:
        dest_colnum_before_dt = cumulative_times.columns.get_loc(RCN_BEFORE_TIMEDELTA)  # noqa
        dest_colnum_during_dt = cumulative_times.columns.get_loc(RCN_DURING_TIMEDELTA)  # noqa
        dest_colnum_after_dt = cumulative_times.columns.get_loc(RCN_AFTER_TIMEDELTA)  # noqa
    else:
        # for type checker
        dest_colnum_before_dt = 0
        dest_colnum_during_dt = 0
        dest_colnum_after_dt = 0
    for rowidx in range(query_nrow):
        patient_id = query_times_df.iat[rowidx, sourcecolnum_pt]
        start = query_times_df.iat[rowidx, sourcecolnum_start]
        when = query_times_df.iat[rowidx, sourcecolnum_when]
        ivlist = timelines[patient_id]
        # log.critical("ivlist: {!r}", ivlist)
        before, during, after = ivlist.cumulative_before_during_after(start,
                                                                      when)
        # log.critical(
        #     "{!r}.cumulative_before_during_after(start={!r}, when={!r}) "
        #     "-> {!r}, {!r}, {!r}",
        #     ivlist, start, when,
        #     before, during, after
        # )
        cumulative_times.iat[rowidx, dest_colnum_pt] = patient_id
        cumulative_times.iat[rowidx, dest_colnum_start] = start
        cumulative_times.iat[rowidx, dest_colnum_t] = when
        cumulative_times.iat[rowidx, dest_colnum_before_days] = before.days
        cumulative_times.iat[rowidx, dest_colnum_during_days] = during.days
        cumulative_times.iat[rowidx, dest_colnum_after_days] = after.days
        if include_timedelta_in_output:
            cumulative_times.iat[rowidx, dest_colnum_before_dt] = before
            cumulative_times.iat[rowidx, dest_colnum_during_dt] = during
            cumulative_times.iat[rowidx, dest_colnum_after_dt] = after
    return cumulative_times


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
    def dateseq(cls, first: str, last: str,
                time_suffix: str = "") -> List[datetime.datetime]:
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
            ]
        )
        drug_events_df = DataFrame.from_records(drug_events_arr)
        log.debug("drug_events_df:\n{!r}", drug_events_df)

        start = datetime.datetime.strptime("2017-01-01" + self.DRUG_EVENT_TIME,
                                           self.DATETIMEFORMAT)
        log.debug("start: {!r}", start)

        qdata_rows = []
        for dt in self.dateseq("2018-01-01", "2018-05-30",
                               time_suffix=self.QUERY_EVENT_TIME):
            qdata_rows.append((alice, start, dt))
        query_times_arr = array(
            qdata_rows,
            dtype=[
                (DEFAULT_PATIENT_COLNAME, DTYPE_STRING),
                (DEFAULT_START_DATETIME_COLNAME, DTYPE_DATETIME),
                (DEFAULT_QUERY_DATETIME_COLNAME, DTYPE_DATETIME),
            ]
        )
        query_times_df = DataFrame.from_records(query_times_arr)
        log.debug("query_times_df:\n{!r}", query_times_df)

        timelines = drug_timelines(
            drug_events_df=drug_events_df,
            event_lasts_for=event_lasts_for,
            patient_colname=DEFAULT_PATIENT_COLNAME,
            event_datetime_colname=DEFAULT_DRUG_EVENT_DATETIME_COLNAME
        )
        log.debug("timelines: {!r}", timelines)

        cumulative = cumulative_time_on_drug(
            drug_events_df=drug_events_df,
            event_lasts_for_timedelta=event_lasts_for,
            query_times_df=query_times_df,
            patient_colname=DEFAULT_PATIENT_COLNAME,
            event_datetime_colname=DEFAULT_DRUG_EVENT_DATETIME_COLNAME,
            start_colname=DEFAULT_START_DATETIME_COLNAME,
            when_colname=DEFAULT_QUERY_DATETIME_COLNAME
        )
        log.debug("cumulative:\n{}", cumulative)


# =============================================================================
# main
# =============================================================================

if __name__ == "__main__":
    main_only_quicksetup_rootlogger(level=logging.DEBUG)
    log.info("Running unit tests")
    unittest.main(argv=[sys.argv[0]])
    sys.exit(0)
