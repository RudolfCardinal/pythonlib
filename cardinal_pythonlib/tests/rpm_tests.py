#!/usr/bin/env python
# cardinal_pythonlib/tests/rpm_tests.py

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

import unittest

import numpy as np
import numpy.typing as npt

from cardinal_pythonlib.rpm import (
    rpm_probabilities_successes_failures,
    rpm_probabilities_successes_totals,
)


# =============================================================================
# Tests
# =============================================================================


class TestRpm(unittest.TestCase):
    def _assert_eq(
        self,
        name: str,
        a1: npt.ArrayLike,
        a2: npt.ArrayLike,
        abs_tolerance: float = 1e-8,
    ) -> None:
        self.assertTrue(
            np.allclose(a1, a2, atol=abs_tolerance),
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
