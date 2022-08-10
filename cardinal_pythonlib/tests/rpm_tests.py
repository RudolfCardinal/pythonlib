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
import unittest

import numpy as np
import numpy.typing as npt
from scipy.stats import beta

from cardinal_pythonlib.rpm import (
    beta_cdf_fast,
    beta_pdf_fast,
    rpm_probabilities_successes_failures,
    rpm_probabilities_successes_totals,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Tests
# =============================================================================


class TestRpm(unittest.TestCase):
    TOLERANCE = 1e-8

    def _assert_eq(
        self,
        name: str,
        a1: npt.ArrayLike,
        a2: npt.ArrayLike,
    ) -> None:
        self.assertTrue(
            np.allclose(a1, a2, atol=self.TOLERANCE),
            f"Error: {name}: {a1} != {a2}",
        )

    def test_rpm(self) -> None:
        p1 = rpm_probabilities_successes_failures(
            n_successes=[0, 0], n_failures=[0, 0]
        )
        self._assert_eq("p1", p1, [0.5, 0.5])

        p2 = rpm_probabilities_successes_totals(
            n_successes=[3, 7], n_total=[10, 10]
        )
        self._assert_eq("p2", p2, [0.04305447, 0.95694553])

        p3 = rpm_probabilities_successes_totals(
            n_successes=[1, 0], n_total=[1, 1]
        )
        self._assert_eq("p3", p3, [0.8333333, 0.1666667])

        self.assertRaises(
            AssertionError,
            rpm_probabilities_successes_totals,
            n_successes=[3, 7],
            n_total=[2, 10],
        )

    def test_fast_beta_distribution_functions(self) -> None:
        """
        Beware not to confuse scipy.stats.beta (as here) with
        scipy.special.beta.
        """
        a_b_max = 20
        for a in range(1, a_b_max + 1):
            for b in range(1, a_b_max + 1):
                for x in np.linspace(0, 1, 20):
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
