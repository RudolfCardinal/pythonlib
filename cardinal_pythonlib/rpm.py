#!/usr/bin/env python
# cardinal_pythonlib/rpm.py

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

**Randomized probability matching (RPM).**

As per:

- Scott SL. A modern Bayesian look at the multi-armed bandit.
  Applied Stochastic Models in Business and Industry 26 (2010): 639–58.
  https://doi.org/10.1002/asmb.874.

An R version is in ``rpm.R`` within https://github.com/rudolfcardinal/rlib.

"""

# =============================================================================
# Imports
# =============================================================================

import logging

import numpy as np
import numpy.typing as npt
from scipy.integrate import quad
from scipy.stats import beta

log = logging.getLogger(__name__)


# =============================================================================
# RPM
# =============================================================================


def rpm_probabilities_successes_failures(
    n_successes: npt.ArrayLike, n_failures: npt.ArrayLike
) -> np.ndarray:
    """
    Calculate the optimal choice probabilities.

    Note that Scott's original R version, compute.probopt(), on Figure 3 (p648)
    has arguments ``y`` (number of successes) and ``n`` (number of trials, NOT
    the number of failures).
    """
    k = len(n_successes)  # k is the number of actions
    assert len(n_failures) == k
    assert np.all(np.greater_equal(n_successes, 0))
    assert np.all(np.greater_equal(n_failures, 0))
    p_choice = np.zeros(shape=[k])  # answer to be populated

    n_successes_plus_one = np.array(n_successes) + 1
    n_failures_plus_one = np.array(n_failures) + 1
    for i in range(k):  # for each action:
        other_actions = list(range(0, i)) + list(range(i + 1, k))

        # Define function to integrate:
        def f(x: float) -> float:
            r = beta(n_successes_plus_one[i], n_failures_plus_one[i]).pdf(x)
            # ... beta density function, for the current action;
            # beta(a, b).pdf(x) is the probability density at x of the beta
            # distribution for a random variable with parameters a and b.
            # The R equivalent is dbeta(x, a, b).
            for j in other_actions:
                r *= beta(n_successes_plus_one[j], n_failures_plus_one[j]).cdf(
                    x
                )
                # ... for the other actions... beta(a, b).cdf(x) is the
                # cumulative distribution function of the beta distribution
                # with parameters a and b (the probability that a random
                # variable with parameters a,b is less than x). The R
                # equivalent is pbeta(x, a, b).
            return r

        # Integrate f from 0 to 1, e.g. via quad():
        # https://docs.scipy.org/doc/scipy/reference/integrate.html
        q = quad(f, 0, 1)[0]
        p_choice[i] = q

    return p_choice


def rpm_probabilities_successes_totals(
    n_successes: npt.ArrayLike, n_total: npt.ArrayLike
) -> np.ndarray:
    """
    Randomized probability matching (RPM).

    Args:
        n_successes:
            Number of successes (per option).
        n_total:
            Total number of trials (per option).

    Returns:
        Optimal choice probabilities (per option) via RPM.
    """
    n_failures = np.array(n_total) - np.array(n_successes)
    return rpm_probabilities_successes_failures(n_successes, n_failures)
