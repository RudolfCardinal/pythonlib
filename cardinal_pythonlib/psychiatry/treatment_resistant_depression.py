#!/usr/bin/env python
# cardinal_pythonlib/psychiatry/treatment_resistant_depression.py

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

**Helper functions for algorithmic definitions of treatment-resistant
depression.**

Performance notes:

- 200 test patients; baseline about 7.65-8.57 seconds (25 Hz).
- From https://stackoverflow.com/questions/19237878/ to
  https://stackoverflow.com/questions/17071871/select-rows-from-a-dataframe-based-on-values-in-a-column-in-pandas  # noqa
- Change from parallel to single-threading: down to 4.38 s (!).
- Avoid a couple of slices: down to 3.85 s for 200 patients.
- Add test patient E; up to 4.63 s for 250 patients (54 Hz).
- On a live set (different test computer), single-threaded: 901.9 s for 4154
  patients (4.6 Hz).
- One pointless indexing call removed: 863.2s for 4154 patients (4.8 Hz).
- Loop boundary tweak: 3.95 s for 300 test patients (76 Hz).
- From iloc to iat: 3.79s (79 Hz)
- These two are very helpful:

  - https://stackoverflow.com/questions/28757389/loc-vs-iloc-vs-ix-vs-at-vs-iat
  - https://medium.com/dunder-data/selecting-subsets-of-data-in-pandas-39e811c81a0c
  
- Switching from tp.loc[conditions] to tp[conditions] didn't make much 
  difference, but the code is a bit cleaner
  
- Anyway, we should profile (see the PROFILE flag). That shows the main time
  is spent in my algorithmic code, not in DataFrame operations.
- Not creating unnecessary results DataFrame objects shaved things down from 
  5.7 to 3.9 s in the profiler.
- Still slower in parallel. Time is spent in thread locking.
- Adjust A loop condition: 3.9 to 3.6s.
- Profiler off: 2.38s for 300 patients, or 126 Hz. Let's call that a day; we've
  achieved a 5-fold speedup.

"""  # noqa

import cProfile
from concurrent.futures import ThreadPoolExecutor
import io
import logging
from multiprocessing import cpu_count
import pstats
from typing import Any, Iterable, List, Optional, Tuple

from numpy import array, NaN, timedelta64
from pandas import DataFrame
from pendulum import DateTime as Pendulum

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger
from cardinal_pythonlib.psychiatry.rfunc import flush_stdout_stderr

log = logging.getLogger(__name__)

DTYPE_STRING = "<U255"
# ... getting this right is surprisingly tricky!
# ... https://docs.scipy.org/doc/numpy-1.13.0/reference/arrays.dtypes.html
# ... https://stackoverflow.com/questions/30086936/what-is-the-difference-between-the-types-type-numpy-string-and-type-str  # noqa
# ... https://stackoverflow.com/questions/49127844/python-convert-python-string-to-numpy-unicode-string  # noqa
DTYPE_DATE = "datetime64[D]"  # D for day resolution, ns for nanoseconds, etc.
# ... https://docs.scipy.org/doc/numpy/reference/arrays.datetime.html

DEFAULT_SOURCE_PATIENT_COLNAME = "patient_id"
DEFAULT_SOURCE_DRUG_COLNAME = "drug"
DEFAULT_SOURCE_DATE_COLNAME = "date"

DEFAULT_ANTIDEPRESSANT_COURSE_LENGTH_DAYS = 28
DEFAULT_EXPECT_RESPONSE_BY_DAYS = 56
DEFAULT_SYMPTOM_ASSESSMENT_TIME_DAYS = 180

RCN_PATIENT_ID = "patient_id"  # RCN: "result column name"
RCN_DRUG_A_NAME = "drug_a_name"
RCN_DRUG_A_FIRST_MENTION = "drug_a_first"
RCN_DRUG_A_SECOND_MENTION = "drug_a_second"
RCN_DRUG_B_NAME = "drug_b_name"
RCN_DRUG_B_FIRST_MENTION = "drug_b_first"
RCN_DRUG_B_SECOND_MENTION = "drug_b_second"
RCN_EXPECT_RESPONSE_BY_DATE = "expect_response_to_b_by"
RCN_END_OF_SYMPTOM_PERIOD = "end_of_symptom_period"

PARALLEL = False
TEST_MANY_FAKE_PATIENTS = False
PROFILE = False

if PARALLEL:
    DEFAULT_N_THREADS = cpu_count()
else:
    DEFAULT_N_THREADS = 1  # faster! About twice as fast for 200 test patients.

if TEST_MANY_FAKE_PATIENTS:
    TEST_PATIENT_MULTIPLE = 50  # for speed testing
else:
    TEST_PATIENT_MULTIPLE = 1  # for debugging


def timedelta_days(days: int) -> timedelta64:
    """
    Convert a duration in days to a NumPy ``timedelta64`` object.
    """
    int_days = int(days)
    if int_days != days:
        raise ValueError("Fractional days passed to timedelta_days: "
                         "{!r}".format(days))
    try:
        # Do not pass e.g. 27.0; that will raise a ValueError.
        # Must be an actual int:
        return timedelta64(int_days, 'D')
    except ValueError as e:
        raise ValueError("Failure in timedelta_days; value was {!r}; original "
                         "error was: {}".format(days, e))


def _get_generic_two_antidep_episodes_result(
        rowdata: Tuple[Any, ...] = None) -> DataFrame:
    """
    Create a results row for this application.
    """
    # Valid data types... see:
    # - pandas.core.dtypes.common.pandas_dtype
    # - https://pandas.pydata.org/pandas-docs/stable/timeseries.html
    # - https://docs.scipy.org/doc/numpy-1.13.0/reference/arrays.datetime.html
    data = [rowdata] if rowdata else []
    return DataFrame(array(
        data,  # data
        dtype=[  # column definitions:
            (RCN_PATIENT_ID, DTYPE_STRING),
            (RCN_DRUG_A_NAME, DTYPE_STRING),
            (RCN_DRUG_A_FIRST_MENTION, DTYPE_DATE),
            (RCN_DRUG_A_SECOND_MENTION, DTYPE_DATE),
            (RCN_DRUG_B_NAME, DTYPE_STRING),
            (RCN_DRUG_B_FIRST_MENTION, DTYPE_DATE),
            (RCN_DRUG_B_SECOND_MENTION, DTYPE_DATE),
            (RCN_EXPECT_RESPONSE_BY_DATE, DTYPE_DATE),
            (RCN_END_OF_SYMPTOM_PERIOD, DTYPE_DATE),
        ]
    ))


def _get_blank_two_antidep_episodes_result() -> DataFrame:
    """
    Returns a blank results row.
    """
    return _get_generic_two_antidep_episodes_result()


def two_antidepressant_episodes_single_patient(
        patient_id: str,
        patient_drug_date_df: DataFrame,
        patient_colname: str = DEFAULT_SOURCE_PATIENT_COLNAME,
        drug_colname: str = DEFAULT_SOURCE_DRUG_COLNAME,
        date_colname: str = DEFAULT_SOURCE_DATE_COLNAME,
        course_length_days: int = DEFAULT_ANTIDEPRESSANT_COURSE_LENGTH_DAYS,
        expect_response_by_days: int = DEFAULT_EXPECT_RESPONSE_BY_DAYS,
        symptom_assessment_time_days: int =
        DEFAULT_SYMPTOM_ASSESSMENT_TIME_DAYS) -> Optional[DataFrame]:
    """
    Processes a single patient for ``two_antidepressant_episodes()`` (q.v.).

    Implements the key algorithm.
    """
    log.debug("Running two_antidepressant_episodes_single_patient() for "
              "patient {!r}".format(patient_id))
    flush_stdout_stderr()
    # Get column details from source data
    sourcecolnum_drug = patient_drug_date_df.columns.get_loc(drug_colname)
    sourcecolnum_date = patient_drug_date_df.columns.get_loc(date_colname)

    # -------------------------------------------------------------------------
    # Get data for this patient
    # -------------------------------------------------------------------------
    # ... this is pretty quick (e.g. 4ms for 1150 rows
    patient_mask = patient_drug_date_df[patient_colname].values == patient_id
    tp = patient_drug_date_df[patient_mask]  # type: DataFrame

    # -------------------------------------------------------------------------
    # Sort by date, then drug.
    # ... arbitrary drug name order to make the output stable
    # -------------------------------------------------------------------------
    # ... this is about 2ms for small lists; probably not limiting
    # ... seems slower if "inplace=True" is used.
    tp = tp.sort_values(by=[date_colname, drug_colname], ascending=True)

    # log.critical("{!r}".format(tp))

    nrows_all = len(tp)  # https://stackoverflow.com/questions/15943769/
    if nrows_all < 4:  # need A, A, B, B; so minimum #rows is 4
        return None
    end_date = tp.iat[nrows_all - 1, sourcecolnum_date]  # date of last row

    # -------------------------------------------------------------------------
    # Get antidepressants, in the order they appear
    # -------------------------------------------------------------------------
    for first_b_rownum in range(2, nrows_all):
        # ... skip rows 0 and 1, because a drug can't be the second (B) drug
        #     unless there are two mentions of A beforehand.
        # ---------------------------------------------------------------------
        # Check candidate B drug
        # ---------------------------------------------------------------------
        antidepressant_b_name = tp.iat[first_b_rownum, sourcecolnum_drug]
        antidepressant_b_first_mention = tp.iat[first_b_rownum,
                                                sourcecolnum_date]
        earliest_possible_b_second_mention = (
            antidepressant_b_first_mention +
            timedelta_days(course_length_days - 1)
        )
        if earliest_possible_b_second_mention > end_date:
            # Impossible for this to be a B course.
            # Logically unnecessary test, but improves efficiency by skipping
            # the slice operation that follows.
            continue  # try another B
        b_second_mentions = tp[
            (tp[drug_colname] == antidepressant_b_name) &  # same drug
            (tp[date_colname] >= earliest_possible_b_second_mention)
        ]
        if len(b_second_mentions) == 0:
            # No second mention of antidepressant_b_name
            continue  # try another B
        # We only care about the earliest qualifying (completion-of-course)
        # B second mention.
        antidepressant_b_second_mention = b_second_mentions.iat[
            0, sourcecolnum_date]
        # ... this statement could be moved to after the A loop, but that
        #     would sacrifice clarity.

        # ---------------------------------------------------------------------
        # Now find preceding A drug
        # ---------------------------------------------------------------------
        preceding_other_antidepressants = tp[
            (tp[drug_colname] != antidepressant_b_name) &
            # ... A is a different drug to B
            (tp[date_colname] < antidepressant_b_first_mention)
            # ... A is mentioned before B starts
        ]
        nrows_a = len(preceding_other_antidepressants)
        if nrows_a < 2:  # need at least two mentions of A
            # No candidates for A
            continue  # try another B
        # preceding_other_antidepressants remains date-sorted (ascending)
        found_valid_a = False
        antidepressant_a_name = NaN
        antidepressant_a_first_mention = NaN
        antidepressant_a_second_mention = NaN
        for first_a_rownum in range(nrows_a - 1):
            # skip the last row, as that's impossible
            antidepressant_a_name = tp.iat[first_a_rownum, sourcecolnum_drug]
            antidepressant_a_first_mention = tp.iat[first_a_rownum,
                                                    sourcecolnum_date]
            earliest_possible_a_second_mention = (
                antidepressant_a_first_mention +
                timedelta_days(course_length_days - 1)
            )
            if (earliest_possible_a_second_mention >=
                    antidepressant_b_first_mention):
                # Impossible to squeeze in the second A mention before B.
                # Logically unnecessary test, but improves efficiency by
                # skipping the slice operation that follows.
                continue  # try another A
            a_second_mentions = tp[
                (tp[drug_colname] == antidepressant_a_name) &
                # ... same drug
                (tp[date_colname] >= earliest_possible_a_second_mention)
                # ... mentioned late enough after its first mention
            ]
            if len(a_second_mentions) == 0:
                # No second mention of antidepressant_a_name
                continue  # try another A
            # We pick the first possible completion-of-course A second
            # mention:
            antidepressant_a_second_mention = a_second_mentions.iat[
                0, sourcecolnum_date]
            # Make sure B is not mentioned within the A range
            mentions_of_b_within_a_range = tp[
                (tp[drug_colname] == antidepressant_b_name) &
                (tp[date_colname] >= antidepressant_a_first_mention) &
                (tp[date_colname] <= antidepressant_a_second_mention)
            ]
            if len(mentions_of_b_within_a_range) > 0:
                # Nope, chuck out this combination.
                continue  # try another A
            found_valid_a = True
            break
        if not found_valid_a:
            continue  # try another B

        # ---------------------------------------------------------------------
        # OK; here we have found a combination that we like.
        # Add it to the results.
        # ---------------------------------------------------------------------
        # https://stackoverflow.com/questions/19365513/how-to-add-an-extra-row-to-a-pandas-dataframe/19368360  # noqa
        # http://pandas.pydata.org/pandas-docs/stable/indexing.html#setting-with-enlargement  # noqa

        expect_response_by_date = (
            antidepressant_b_first_mention + timedelta_days(
                expect_response_by_days)
        )
        end_of_symptom_period = (
            antidepressant_b_first_mention + timedelta_days(
                expect_response_by_days + symptom_assessment_time_days - 1)
        )
        result = _get_generic_two_antidep_episodes_result((
            patient_id,
            antidepressant_a_name,
            antidepressant_a_first_mention,
            antidepressant_a_second_mention,
            antidepressant_b_name,
            antidepressant_b_first_mention,
            antidepressant_b_second_mention,
            expect_response_by_date,
            end_of_symptom_period
        ))
        # We only care about the first episode per patient that matches, so:
        return result

    return None  # nothing found


def two_antidepressant_episodes(
        patient_drug_date_df: DataFrame,
        patient_colname: str = DEFAULT_SOURCE_PATIENT_COLNAME,
        drug_colname: str = DEFAULT_SOURCE_DRUG_COLNAME,
        date_colname: str = DEFAULT_SOURCE_DATE_COLNAME,
        course_length_days: int = DEFAULT_ANTIDEPRESSANT_COURSE_LENGTH_DAYS,
        expect_response_by_days: int = DEFAULT_EXPECT_RESPONSE_BY_DAYS,
        symptom_assessment_time_days: int =
        DEFAULT_SYMPTOM_ASSESSMENT_TIME_DAYS,
        n_threads: int = DEFAULT_N_THREADS) -> DataFrame:
    """
    Takes a *pandas* ``DataFrame``, ``patient_drug_date_df`` (or, via
    ``reticulate``, an R ``data.frame`` or ``data.table``). This should contain
    dated present-tense references to antidepressant drugs (only).

    Returns a set of result rows as a ``DataFrame``.
    """
    # Say hello
    log.info("Running two_antidepressant_episodes...")
    start = Pendulum.now()

    # Work through each patient
    patient_ids = sorted(list(set(patient_drug_date_df[patient_colname])))
    n_patients = len(patient_ids)
    log.info("Found {} patients".format(n_patients))
    flush_stdout_stderr()

    def _get_patient_result(_patient_id: str) -> Optional[DataFrame]:
        return two_antidepressant_episodes_single_patient(
            patient_id=_patient_id,
            patient_drug_date_df=patient_drug_date_df,
            patient_colname=patient_colname,
            drug_colname=drug_colname,
            date_colname=date_colname,
            course_length_days=course_length_days,
            expect_response_by_days=expect_response_by_days,
            symptom_assessment_time_days=symptom_assessment_time_days
        )

    combined_result = _get_blank_two_antidep_episodes_result()
    if n_threads > 1:
        # Farm off the work to lots of threads:
        log.info("Parallel processing method; {} threads".format(n_threads))
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            list_of_results_frames = executor.map(_get_patient_result,
                                                  patient_ids)

        log.debug("Recombining results from parallel processing...")
        for patient_result in list_of_results_frames:
            if patient_result is not None:
                combined_result = combined_result.append(patient_result)
        log.debug("... recombined")

    else:
        log.info("Single-thread method")
        for ptnum, patient_id in enumerate(patient_ids, start=1):
            log.debug("Processing patient {} out of {}".format(
                ptnum, n_patients))
            patient_result = _get_patient_result(patient_id)
            if patient_result is not None:
                combined_result = combined_result.append(patient_result)

    # For consistent results order, even with parallel processing:
    combined_result = combined_result.sort_values(
        by=[RCN_PATIENT_ID], ascending=True)
    # So that the DataFrame indices aren't all zero (largely cosmetic):
    combined_result.reset_index(inplace=True, drop=True)

    end = Pendulum.now()
    duration = end - start
    log.info("Took {} seconds for {} patients".format(
        duration.total_seconds(), n_patients))
    flush_stdout_stderr()
    return combined_result


def test_two_antidepressant_episodes(
        n_sets: int = TEST_PATIENT_MULTIPLE) -> None:
    fluox = "fluoxetine"
    cital = "citalopram"
    sert = "sertraline"
    mirtaz = "mirtazapine"
    venla = "venlafaxine"

    alice = "Alice"
    bob = "Bob"
    chloe = "Chloe"
    dave = "Dave"
    elsa = "Elsa"
    fred = "Fred"
    grace = "Grace"

    def _make_example(suffixes: Iterable[Any] = None) -> DataFrame:
        suffixes = suffixes or [""]  # type: List[str]
        # https://docs.scipy.org/doc/numpy-1.10.1/user/basics.rec.html
        # https://github.com/pandas-dev/pandas/issues/12751
        dataframe = None
        for suffix in suffixes:
            s = str(suffix)
            alice_s = alice + s
            bob_s = bob + s
            chloe_s = chloe + s
            dave_s = dave + s
            elsa_s = elsa + s
            fred_s = fred + s
            grace_s = grace + s
            arr = array(
                [
                    # Bob: mixture switch; should pick mirtaz -> sert
                    (bob_s, venla, "2018-01-01"),
                    (bob_s, mirtaz, "2018-01-01"),
                    (bob_s, venla, "2018-02-01"),
                    (bob_s, mirtaz, "2018-02-01"),
                    (bob_s, venla, "2018-03-01"),
                    (bob_s, sert, "2018-03-02"),
                    (bob_s, venla, "2018-04-01"),
                    (bob_s, sert, "2018-05-01"),
                    (bob_s, sert, "2018-06-01"),
                    # Alice: two consecutive switches; should pick the first, c -> f  # noqa
                    # ... goes second in the data; should be sorted to first
                    (alice_s, cital, "2018-01-01"),
                    (alice_s, cital, "2018-02-01"),
                    (alice_s, fluox, "2018-03-01"),
                    (alice_s, fluox, "2018-04-01"),
                    (alice_s, mirtaz, "2018-05-01"),
                    (alice_s, mirtaz, "2018-06-01"),
                    # Chloe: courses just too short; should give nothing
                    (chloe_s, fluox, "2018-01-01"),
                    (chloe_s, fluox, "2018-01-27"),
                    (chloe_s, venla, "2018-02-01"),
                    (chloe_s, venla, "2018-01-27"),
                    # Dave: courses just long enough
                    (dave_s, fluox, "2018-01-01"),
                    (dave_s, fluox, "2018-01-28"),
                    (dave_s, venla, "2018-02-01"),
                    (dave_s, venla, "2018-02-28"),
                    # Elsa: courses overlap; invalid
                    (elsa_s, cital, "2018-01-01"),
                    (elsa_s, cital, "2018-02-05"),
                    (elsa_s, mirtaz, "2018-02-01"),
                    (elsa_s, mirtaz, "2018-02-28"),
                    # Fred: courses overlap, same day; invalid
                    (fred_s, cital, "2018-01-01"),
                    (fred_s, cital, "2018-02-01"),
                    (fred_s, mirtaz, "2018-02-01"),
                    (fred_s, mirtaz, "2018-02-28"),
                    # Grace: multiple potentials; should pick cital -> fluox
                    (grace_s, cital, "2018-01-01"),
                    (grace_s, cital, "2018-01-28"),
                    (grace_s, fluox, "2018-02-01"),
                    (grace_s, venla, "2018-02-02"),
                    (grace_s, fluox, "2018-02-28"),
                    (grace_s, venla, "2018-03-01"),
                    (grace_s, mirtaz, "2018-04-01"),
                    (grace_s, mirtaz, "2018-04-28"),
                ],
                dtype=[
                    (patient_colname, DTYPE_STRING),
                    (drug_colname, DTYPE_STRING),
                    (date_colname, DTYPE_DATE),
                ]
            )
            newpart = DataFrame.from_records(arr)
            if dataframe is None:
                dataframe = newpart
            else:
                dataframe = dataframe.append(newpart)
        return dataframe

    def _validate(_result: DataFrame, patient_name: str,
                  nrows: int, drug_a: str = None, drug_b: str = None) -> None:
        colnum_drug_a = _result.columns.get_loc(RCN_DRUG_A_NAME)
        colnum_drug_b = _result.columns.get_loc(RCN_DRUG_B_NAME)
        patient_result = _result[_result[RCN_PATIENT_ID] == patient_name]
        assert len(patient_result) == nrows
        if nrows != 1:
            return
        assert patient_result.iat[0, colnum_drug_a] == drug_a
        assert patient_result.iat[0, colnum_drug_b] == drug_b

    patient_colname = "BrcId"  # DEFAULT_SOURCE_PATIENT_COLNAME
    drug_colname = "generic_drug"  # DEFAULT_SOURCE_DRUG_COLNAME
    date_colname = "Document_Date"  # DEFAULT_SOURCE_DATE_COLNAME

    log.warning("Testing two_antidepressant_episodes()")
    testdata = _make_example(suffixes=[] if n_sets == 1 else range(n_sets))
    # log.info("Data array:\n" + repr(arr))
    log.info("Data:\n" + repr(testdata))
    flush_stdout_stderr()
    result = two_antidepressant_episodes(
        patient_drug_date_df=testdata,
        patient_colname=patient_colname,
        drug_colname=drug_colname,
        date_colname=date_colname,
        course_length_days=DEFAULT_ANTIDEPRESSANT_COURSE_LENGTH_DAYS,
        expect_response_by_days=DEFAULT_EXPECT_RESPONSE_BY_DAYS,
        symptom_assessment_time_days=DEFAULT_SYMPTOM_ASSESSMENT_TIME_DAYS,
    )
    log.info("Result:\n" + result.to_string())
    if n_sets == 1:
        # Proper validation
        log.warning("Test complete; will now validate.")
        _validate(result, alice, 1, cital, fluox)
        _validate(result, bob, 1, mirtaz, sert)
        _validate(result, chloe, 0)
        _validate(result, dave, 1, fluox, venla)
        _validate(result, elsa, 0)
        _validate(result, fred, 0)
        _validate(result, grace, 1, cital, fluox)
        log.warning("Validation successful.")
    else:
        log.warning("Speed test complete.")
    flush_stdout_stderr()


def main() -> None:
    main_only_quicksetup_rootlogger(level=logging.DEBUG, with_thread_id=True)

    if PROFILE:
        pr = cProfile.Profile()
        pr.enable()

        test_two_antidepressant_episodes()

        pr.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        # In Python 3.7: sortby = pstats.SortKey.CUMULATIVE
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats(50)  # top 50
        print(s.getvalue())

    else:
        test_two_antidepressant_episodes()


if __name__ == "__main__":
    main()
