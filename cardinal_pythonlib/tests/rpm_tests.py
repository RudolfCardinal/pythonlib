#!/usr/bin/env python
# cardinal_pythonlib/tests/rpm_tests.py

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

import logging
from typing import Set, Tuple
import unittest

import numpy as np
import numpy.typing as npt
from scipy.stats import beta

from cardinal_pythonlib.rpm import (
    beta_cdf_fast,
    beta_pdf_fast,
    rpm_probabilities_successes_failures,
    rpm_probabilities_successes_failures_fast,
    rpm_probabilities_successes_failures_twochoice_fast,
    rpm_probabilities_successes_totals,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Tests
# =============================================================================


class TestRpm(unittest.TestCase):
    TOLERANCE = 1e-8

    def assert_arrays_eq(
        self,
        a1: npt.ArrayLike,
        a2: npt.ArrayLike,
    ) -> None:
        self.assertTrue(
            np.allclose(a1, a2, atol=self.TOLERANCE),
            f"Error: {a1} != {a2}",
        )

    def test_rpm_pure_python(self) -> None:
        """
        Compare some values to specific values ascertained via R.
        """
        p1 = rpm_probabilities_successes_failures(
            n_successes=[0, 0], n_failures=[0, 0]
        )
        self.assert_arrays_eq(p1, [0.5, 0.5])

        p2 = rpm_probabilities_successes_totals(
            n_successes=[3, 7], n_total=[10, 10]
        )
        self.assert_arrays_eq(p2, [0.04305447, 0.95694553])

        p3 = rpm_probabilities_successes_totals(
            n_successes=[1, 0], n_total=[1, 1]
        )
        self.assert_arrays_eq(p3, [0.8333333, 0.1666667])

    def test_rpm_successes_totals(self) -> None:
        """
        Check the sanity checks.
        """
        self.assertRaises(
            AssertionError,
            rpm_probabilities_successes_totals,
            n_successes=[3, 7],
            n_total=[2, 10],
        )

    def test_fast_beta_distribution_functions(self) -> None:
        """
        Test our jit-compiled beta distribution functions, versus scipy's
        trusted but slow versions.

        Beware not to confuse scipy.stats.beta (as here) with
        scipy.special.beta.
        """
        a_b_max = 10
        n_x_divisions = 11
        for a in range(1, a_b_max + 1):
            for b in range(1, a_b_max + 1):
                for x in np.linspace(0, 1, n_x_divisions):
                    # logger.critical(f"Testing beta: x={x}, a={a}, b={b}")

                    # PDF
                    self.assertAlmostEqual(
                        beta(a, b).pdf(x),
                        beta.pdf(x, a, b),
                        delta=self.TOLERANCE,
                    )
                    self.assertAlmostEqual(
                        beta_pdf_fast(x, a, b),
                        beta.pdf(x, a, b),
                        delta=self.TOLERANCE,
                    )

                    # CDF
                    self.assertAlmostEqual(
                        beta(a, b).cdf(x),
                        beta.cdf(x, a, b),
                        delta=self.TOLERANCE,
                    )
                    self.assertAlmostEqual(
                        beta_cdf_fast(x, a, b),
                        beta.cdf(x, a, b),
                        delta=self.TOLERANCE,
                    )

    def test_fast_rpm_twochoice(self) -> None:
        """
        Test rpm_probabilities_successes_failures_twochoice_fast() against
        rpm_probabilities_successes_totals().
        """
        seen = set()  # type: Set[Tuple[int, int, int, int]]
        max_val = 5
        for success_this in range(max_val + 1):
            for failure_this in range(max_val + 1):
                for success_other in range(max_val + 1):
                    for failure_other in range(max_val + 1):
                        forwards = (
                            success_this,
                            failure_this,
                            success_other,
                            failure_other,
                        )
                        backwards = (
                            success_other,
                            failure_other,
                            success_this,
                            failure_this,
                        )
                        if backwards in seen:
                            continue
                        seen.add(forwards)
                        successes = [success_this, success_other]
                        failures = [failure_this, failure_other]
                        p_fast_this = rpm_probabilities_successes_failures_twochoice_fast(  # noqa: E501
                            success_this,
                            failure_this,
                            success_other,
                            failure_other,
                        )
                        p_fast = [p_fast_this, 1 - p_fast_this]
                        self.assert_arrays_eq(
                            p_fast,
                            rpm_probabilities_successes_failures(
                                successes, failures
                            ),
                        )

    def test_fast_rpm_n_choice(self) -> None:
        """
        Tests with an arbitrary number of actions.
        """
        successes_failures = (
            ((2, 3), (4, 5)),
            ((0, 0, 0), (0, 0, 0)),
            ((1, 0, 3, 4), (2, 5, 3, 9)),
            ((0, 1, 2, 3, 4), (5, 6, 7, 8, 9)),
        )
        for successes, failures in successes_failures:
            self.assert_arrays_eq(
                rpm_probabilities_successes_failures_fast(successes, failures),
                rpm_probabilities_successes_failures(successes, failures),
            )
