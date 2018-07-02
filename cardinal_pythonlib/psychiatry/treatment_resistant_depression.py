#!/usr/bin/env python
# cardinal_pythonlib/psychiatry/treatment_resistant_depression.py

"""
===============================================================================

    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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

Helper functions for algorithmic definitions of treatment-resistant depression.

"""

import logging

import numpy as np
from numpy import array, NaN, timedelta64
from pandas import DataFrame, Series

from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger

log = logging.getLogger(__name__)

DTYPE_STRING = "<U255"
# ... https://docs.scipy.org/doc/numpy-1.13.0/reference/arrays.dtypes.html
# ... https://stackoverflow.com/questions/30086936/what-is-the-difference-between-the-types-type-numpy-string-and-type-str  # noqa
# ... https://stackoverflow.com/questions/49127844/python-convert-python-string-to-numpy-unicode-string  # noqa
DTYPE_DATE = "datetime64[ns]"

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


def timedelta_days(days: int) -> timedelta64:
    return timedelta64(days, 'D')


def two_antidepressant_episodes(
        patient_drug_date_df: DataFrame,
        patient_colname: str = DEFAULT_SOURCE_PATIENT_COLNAME,
        drug_colname: str = DEFAULT_SOURCE_DRUG_COLNAME,
        date_colname: str = DEFAULT_SOURCE_DATE_COLNAME,
        course_length_days: int = DEFAULT_ANTIDEPRESSANT_COURSE_LENGTH_DAYS,
        expect_response_by_days: int = DEFAULT_EXPECT_RESPONSE_BY_DAYS,
        symptom_assessment_time_days: int =
        DEFAULT_SYMPTOM_ASSESSMENT_TIME_DAYS) -> DataFrame:
    """
    Takes a pandas DataFrame (or, via reticulate, an R data.frame or
    data.table).
    """
    # Get column details from source data
    sourcecolnum_drug = patient_drug_date_df.columns.get_loc(drug_colname)
    sourcecolnum_date = patient_drug_date_df.columns.get_loc(date_colname)

    # Set up results grid
    # Valid data types... see:
    # - pandas.core.dtypes.common.pandas_dtype
    # - https://pandas.pydata.org/pandas-docs/stable/timeseries.html
    # - https://docs.scipy.org/doc/numpy-1.13.0/reference/arrays.datetime.html

    result = DataFrame(array(
        [],  # data
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

    # Work through each patient
    patient_ids = sorted(list(set(patient_drug_date_df[patient_colname])))
    for pid in patient_ids:
        # Get data for this patient
        tp = patient_drug_date_df.loc[
            (patient_drug_date_df[patient_colname] == pid)
        ]  # type: DataFrame  # tp: "this patient"
        # ... https://stackoverflow.com/questions/19237878/

        # Sort by date
        tp = tp.sort_values(by=date_colname, ascending=True)

        # Get antidepressants, in the order they appear
        nrows_all = len(tp)  # https://stackoverflow.com/questions/15943769/
        for first_b_rownum in range(nrows_all):
            # -----------------------------------------------------------------
            # Check candidate B drug
            # -----------------------------------------------------------------
            antidepressant_b_name = tp.iloc[first_b_rownum, sourcecolnum_drug]
            antidepressant_b_first_mention = tp.iloc[first_b_rownum,
                                                     sourcecolnum_date]
            earliest_possible_b_second_mention = (
                    antidepressant_b_first_mention +
                    timedelta_days(course_length_days - 1)
            )
            b_second_mentions = tp.loc[
                (tp[drug_colname] == antidepressant_b_name) &  # same drug
                (tp[date_colname] >= earliest_possible_b_second_mention)
            ]
            if len(b_second_mentions) == 0:
                # No second mention of antidepressant_b_name
                continue
            # We only care about the earliest qualifying (completion-of-course)
            # B second mention.
            antidepressant_b_second_mention = b_second_mentions.iloc[
                0, sourcecolnum_date]

            # -----------------------------------------------------------------
            # Now find preceding A drug
            # -----------------------------------------------------------------
            preceding_other_antidepressants = tp.loc[
                (tp[drug_colname] != antidepressant_b_name) &
                # ... A is a different drug to B
                (tp[date_colname] < antidepressant_b_first_mention)
                # ... A is mentioned before B starts
            ]
            nrows_a = len(preceding_other_antidepressants)
            if nrows_a == 0:
                # No candidates for A
                continue
            # preceding_other_antidepressants remains date-sorted (ascending)
            found_valid_a = False
            antidepressant_a_name = NaN
            antidepressant_a_first_mention = NaN
            antidepressant_a_second_mention = NaN
            for first_a_rownum in range(nrows_a):
                antidepressant_a_name = tp.iloc[first_a_rownum,
                                                sourcecolnum_drug]
                antidepressant_a_first_mention = tp.iloc[first_a_rownum,
                                                         sourcecolnum_date]
                earliest_possible_a_second_mention = (
                        antidepressant_a_first_mention +
                        timedelta_days(course_length_days - 1)
                )
                a_second_mentions = tp.loc[
                    (tp[drug_colname] == antidepressant_a_name) &
                    # ... same drug
                    (tp[date_colname] >= earliest_possible_a_second_mention)
                    # ... mentioned late enough after its first mention
                ]
                if len(a_second_mentions) == 0:
                    # No second mention of antidepressant_a_name
                    continue
                # We pick the first possible completion-of-course A second
                # mention
                antidepressant_a_second_mention = a_second_mentions.iloc[
                    0, sourcecolnum_date]
                # Make sure B is not mentioned within the A range
                mentions_of_b_within_a_range = tp.loc[
                    (tp[drug_colname] == antidepressant_b_name) &
                    (tp[date_colname] >= antidepressant_a_first_mention) &
                    (tp[date_colname] <= antidepressant_a_second_mention)
                ]
                if len(mentions_of_b_within_a_range) > 0:
                    # Nope, chuck out this combination.
                    continue
                found_valid_a = True
                break
            if not found_valid_a:
                continue

            # -----------------------------------------------------------------
            # OK; here we have found a combination that we like.
            # Add it to the results.
            # -----------------------------------------------------------------
            # https://stackoverflow.com/questions/19365513/how-to-add-an-extra-row-to-a-pandas-dataframe/19368360  # noqa
            # http://pandas.pydata.org/pandas-docs/stable/indexing.html#setting-with-enlargement  # noqa
            result.loc[len(result)] = [
                pid,
                antidepressant_a_name,
                antidepressant_a_first_mention,
                antidepressant_a_second_mention,
                antidepressant_b_name,
                antidepressant_b_first_mention,
                antidepressant_b_second_mention,
                NaN,
                NaN
            ]

    # Fill in dates:
    result[RCN_EXPECT_RESPONSE_BY_DATE] = (
            result[RCN_DRUG_B_FIRST_MENTION] +
            timedelta_days(expect_response_by_days)
    )
    result[RCN_END_OF_SYMPTOM_PERIOD] = (
            result[RCN_DRUG_B_FIRST_MENTION] +
            timedelta_days(
                expect_response_by_days + symptom_assessment_time_days - 1)
    )

    # Done:
    return result


def _test_two_antidepressant_episodes() -> None:
    log.warning("Testing two_antidepressant_episodes()")
    alice = "Alice"
    bob = "Bob"
    chloe = "Chloe"
    fluox = "fluoxetine"
    cital = "citalopram"
    sert = "sertraline"
    mirtaz = "mirtazapine"
    venla = "venlafaxine"
    # https://docs.scipy.org/doc/numpy-1.10.1/user/basics.rec.html
    # https://github.com/pandas-dev/pandas/issues/12751
    patient_colname = "BrcId"  # DEFAULT_SOURCE_PATIENT_COLNAME
    drug_colname = "generic_drug"  # DEFAULT_SOURCE_DRUG_COLNAME
    date_colname = "Document_Date"  # DEFAULT_SOURCE_DATE_COLNAME
    arr = array(
        [
            # Alice
            (alice, cital, "2018-01-01"),
            (alice, cital, "2018-02-01"),
            (alice, fluox, "2018-03-01"),
            (alice, fluox, "2018-04-01"),
            (alice, mirtaz, "2018-05-01"),
            (alice, mirtaz, "2018-06-01"),
            # Bob
            (bob, venla, "2018-01-01"),
            (bob, mirtaz, "2018-01-01"),
            (bob, venla, "2018-02-01"),
            (bob, mirtaz, "2018-02-01"),
            (bob, venla, "2018-03-01"),
            (bob, sert, "2018-03-02"),
            (bob, venla, "2018-04-01"),
            (bob, sert, "2018-05-01"),
            (bob, sert, "2018-06-01"),
        ],
        dtype=[
            (patient_colname, DTYPE_STRING),
            (drug_colname, DTYPE_STRING),
            (date_colname, DTYPE_DATE),
        ]
    )
    testdata = DataFrame.from_records(arr)
    # log.info("Data array:\n" + repr(arr))
    log.info("Data:\n" + repr(testdata))
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
    log.warning("Test complete; check output above.")


if __name__ == "__main__":
    main_only_quicksetup_rootlogger(level=logging.DEBUG)
    _test_two_antidepressant_episodes()
