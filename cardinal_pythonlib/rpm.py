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
from typing import Callable

from math import exp, fabs, isinf, inf, lgamma, log, log1p, pi, sqrt
from numba.core.decorators import cfunc, jit
from numba.core.types import CPointer, float64, intc
from numba.np.numpy_support import carray
from scipy import LowLevelCallable
from scipy.integrate import quad
from scipy.stats import beta
import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

NaN = float("nan")


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
    # noinspection DuplicatedCode
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


# =============================================================================
# Helper functions: Fast maths functions for RPM
# =============================================================================


@jit(nopython=True)
def incbeta(x: float, a: float, b: float) -> float:
    """
    - This is an implementation of the regularized incomplete beta function, or
      beta distribution cumulative distribution function (CDF).
    - Translated and adapted from
      https://github.com/codeplea/incbeta/blob/master/incbeta.c.
    - Found via
      https://stats.stackexchange.com/questions/399279/efficiently-computing-the-beta-cdf.
    - See self-tests to check that it does the right thing.
    - See also https://en.wikipedia.org/wiki/Beta_distribution.
    - In R: plot(function(x) pbeta(x, shape1 = a, shape2 = b))
    - See https://github.com/SurajGupta/r-source/blob/master/src/nmath/pbeta.c

    Original license:

    .. code-block:: none

        /*
         * zlib License
         *
         * Regularized Incomplete Beta Function
         *
         * Copyright (c) 2016, 2017 Lewis Van Winkle
         * https://CodePlea.com
         *
         * This software is provided 'as-is', without any express or implied
         * warranty. In no event will the authors be held liable for any damages
         * arising from the use of this software.
         *
         * Permission is granted to anyone to use this software for any purpose,
         * including commercial applications, and to alter it and redistribute it
         * freely, subject to the following restrictions:
         *
         * 1. The origin of this software must not be misrepresented; you must not
         *    claim that you wrote the original software. If you use this software
         *    in a product, an acknowledgement in the product documentation would be
         *    appreciated but is not required.
         * 2. Altered source versions must be plainly marked as such, and must not be
         *    misrepresented as being the original software.
         * 3. This notice may not be removed or altered from any source distribution.
         */

    """  # noqa
    # logger.critical(f"incbeta(x={x}, a={a}, b={b})")

    if a <= 0.0 or b <= 0.0:
        # We require a > 0, b > 0
        return NaN
    if x < 0.0 or x > 1.0:
        # logger.critical("out of range -> nan")
        return NaN  # CDF is only defined for x in [0, 1]
    if x <= 0.0:
        # logger.critical("fast -> 0.0")
        return 0.0  # CDF is zero at x = 0; avoid calculating log(0)
    if x >= 1.0:
        # logger.critical("fast -> 1.0")
        return 1.0  # CDF is one at x = 1; avoid calculating log(0)

    # The continued fraction converges nicely for x < (a+1)/(a+b+2)
    if x > (a + 1.0) / (a + b + 2.0):
        # Use the fact that beta is symmetrical.
        # Swap a and b. Swap x for 1 - x.
        result = 1.0 - incbeta(1.0 - x, b, a)
        # logger.critical(f"symmetrical -> {result}")
        return result

    # Find the first part before the continued fraction.
    lbeta_ab = lgamma(a) + lgamma(b) - lgamma(a + b)
    front = exp(log(x) * a + log(1.0 - x) * b - lbeta_ab) / a

    # Use Lentz's algorithm to evaluate the continued fraction.
    f = 1.0
    c = 1.0
    d = 0.0

    n_loops = 200
    stop = 1.0e-8
    tiny = 1.0e-30
    for i in range(n_loops + 1):
        m = int(i / 2)

        if i == 0:
            numerator = 1.0  # First numerator is 1.0.
        elif i % 2 == 0:
            numerator = (m * (b - m) * x) / (
                (a + 2.0 * m - 1.0) * (a + 2.0 * m)
            )  # Even term.
        else:
            numerator = -((a + m) * (a + b + m) * x) / (
                (a + 2.0 * m) * (a + 2.0 * m + 1)
            )  # Odd term.

        # Do an iteration of Lentz's algorithm.
        d = 1.0 + numerator * d
        if fabs(d) < tiny:
            d = tiny
        d = 1.0 / d

        c = 1.0 + numerator / c
        if fabs(c) < tiny:
            c = tiny

        cd = c * d
        f *= cd

        # Check for stop.
        if fabs(1.0 - cd) < stop:
            result = front * (f - 1.0)
            # logger.critical(f"converged -> {result}")
            return result

    return NaN  # Needed more loops, did not converge.


beta_cdf_fast = incbeta


@jit(nopython=True)
def stirlerr(n: float) -> float:
    """
    Stirling expansion error. Translated and adapted from
    https://github.com/atks/Rmath/blob/master/stirlerr.c

    Original license:

    .. code-block:: none

        /*
         *  AUTHOR
         *    Catherine Loader, catherine@research.bell-labs.com.
         *    October 23, 2000.
         *
         *  Merge in to R:
         *	Copyright (C) 2000, The R Core Team
         *
         *  This program is free software; you can redistribute it and/or modify
         *  it under the terms of the GNU General Public License as published by
         *  the Free Software Foundation; either version 2 of the License, or
         *  (at your option) any later version.
         *
         *  This program is distributed in the hope that it will be useful,
         *  but WITHOUT ANY WARRANTY; without even the implied warranty of
         *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
         *  GNU General Public License for more details.
         *
         *  You should have received a copy of the GNU General Public License
         *  along with this program; if not, a copy is available at
         *  https://www.r-project.org/Licenses/
         *
         *
         *  DESCRIPTION
         *
         *    Computes the log of the error term in Stirling's formula.
         *      For n > 15, uses the series 1/12n - 1/360n^3 + ...
         *      For n <=15, integers or half-integers, uses stored values.
         *      For other n < 15, uses lgamma directly (don't use this to
         *        write lgamma!)
         *
         * Merge in to R:
         * Copyright (C) 2000, The R Core Team
         * R has lgammafn, and lgamma is not part of ISO C
         */

    """  # noqa
    s0 = 0.083333333333333333333  # 1/12
    s1 = 0.00277777777777777777778  # 1/360
    s2 = 0.00079365079365079365079365  # 1/1260
    s3 = 0.000595238095238095238095238  # 1/1680
    s4 = 0.0008417508417508417508417508  # 1/1188

    # error for 0, 0.5, 1.0, 1.5, ..., 14.5, 15.0.
    sferr_halves = [
        0.0,  # n=0 - wrong, place holder only
        0.1534264097200273452913848,  # 0.5
        0.0810614667953272582196702,  # 1.0
        0.0548141210519176538961390,  # 1.5
        0.0413406959554092940938221,  # 2.0
        0.03316287351993628748511048,  # 2.5
        0.02767792568499833914878929,  # 3.0
        0.02374616365629749597132920,  # 3.5
        0.02079067210376509311152277,  # 4.0
        0.01848845053267318523077934,  # 4.5
        0.01664469118982119216319487,  # 5.0
        0.01513497322191737887351255,  # 5.5
        0.01387612882307074799874573,  # 6.0
        0.01281046524292022692424986,  # 6.5
        0.01189670994589177009505572,  # 7.0
        0.01110455975820691732662991,  # 7.5
        0.010411265261972096497478567,  # 8.0
        0.009799416126158803298389475,  # 8.5
        0.009255462182712732917728637,  # 9.0
        0.008768700134139385462952823,  # 9.5
        0.008330563433362871256469318,  # 10.0
        0.007934114564314020547248100,  # 10.5
        0.007573675487951840794972024,  # 11.0
        0.007244554301320383179543912,  # 11.5
        0.006942840107209529865664152,  # 12.0
        0.006665247032707682442354394,  # 12.5
        0.006408994188004207068439631,  # 13.0
        0.006171712263039457647532867,  # 13.5
        0.005951370112758847735624416,  # 14.0
        0.005746216513010115682023589,  # 14.5
        0.005554733551962801371038690,  # 15.0
    ]
    if n <= 15.0:
        nn = n + n
        if nn == int(nn):
            return sferr_halves[int(nn)]
        return lgamma(n + 1.0) - (n + 0.5) * log(n) + n - log(sqrt(2 * pi))

    nn = n * n
    if n > 500:
        return (s0 - s1 / nn) / n
    if n > 80:
        return (s0 - (s1 - s2 / nn) / nn) / n
    if n > 35:
        return (s0 - (s1 - (s2 - s3 / nn) / nn) / nn) / n
    # 15 < n <= 35 :
    return (s0 - (s1 - (s2 - (s3 - s4 / nn) / nn) / nn) / nn) / n


@jit(nopython=True)
def bd0(x: float, np_: float) -> float:
    """
    Per https://github.com/atks/Rmath/blob/master/bd0.c.
    """
    if isinf(x) or isinf(np_) or np_ == 0.0:
        return NaN

    if fabs(x - np_) < 0.1 * (x + np_):
        v = (x - np_) / (x + np_)
        s = (x - np_) * v  # s using v -- change by MM
        ej = 2 * x * v
        v = v * v
        j = 1
        while True:  # Taylor series
            ej *= v
            s1 = s + ej / ((j << 1) + 1)
            if s1 == s:  # last term was effectively 0
                return s1
            s = s1
            j += 1
    return x * log(x / np_) + np_ - x


@jit(nopython=True)
def dbinom_raw_log(x: float, n: float, p: float, q: float) -> float:
    """
    Translated and adapted from
    https://github.com/atks/Rmath/blob/master/dbinom.c -- the version where
    give_log is TRUE, for which:

    - R_D_exp(x) translates to x
    - R_D__0 translates to -inf
    - R_D__1 translates to 0

    Original license:

    .. code-block:: none

        /*
         * AUTHOR
         *   Catherine Loader, catherine@research.bell-labs.com.
         *   October 23, 2000.
         *
         *  Merge in to R and further tweaks :
         *	Copyright (C) 2000, The R Core Team
         *	Copyright (C) 2008, The R Foundation
         *
         *  This program is free software; you can redistribute it and/or modify
         *  it under the terms of the GNU General Public License as published by
         *  the Free Software Foundation; either version 2 of the License, or
         *  (at your option) any later version.
         *
         *  This program is distributed in the hope that it will be useful,
         *  but WITHOUT ANY WARRANTY; without even the implied warranty of
         *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
         *  GNU General Public License for more details.
         *
         *  You should have received a copy of the GNU General Public License
         *  along with this program; if not, a copy is available at
         *  https://www.r-project.org/Licenses/
         *
         *
         * DESCRIPTION
         *
         *   To compute the binomial probability, call dbinom(x,n,p).
         *   This checks for argument validity, and calls dbinom_raw().
         *
         *   dbinom_raw() does the actual computation; note this is called by
         *   other functions in addition to dbinom().
         *     (1) dbinom_raw() has both p and q arguments, when one may be represented
         *         more accurately than the other (in particular, in df()).
         *     (2) dbinom_raw() does NOT check that inputs x and n are integers. This
         *         should be done in the calling function, where necessary.
         *         -- but is not the case at all when called e.g., from df() or dbeta() !
         *     (3) Also does not check for 0 <= p <= 1 and 0 <= q <= 1 or NaN's.
         *         Do this in the calling function.
         */

    """  # noqa
    log_0 = -inf
    log_1 = 0

    if p == 0:
        return log_1 if x == 0 else log_0
    if q == 0:
        return log_1 if x == n else log_0

    if x == 0:
        if n == 0:
            return log_1
        if p < 0.1:
            lc = -bd0(n, n * q) - n * p
        else:
            lc = n * log(q)
        return lc

    if x == n:
        if q < 0.1:
            lc = -bd0(n, n * p) - n * q
        else:
            lc = n * log(p)
        return lc

    if x < 0 or x > n:
        return log_0

    # n*p or n*q can underflow to zero if n and p or q are small.  This
    # used to occur in dbeta, and gives NaN as from R 2.3.0.
    lc = (
        stirlerr(n)
        - stirlerr(x)
        - stirlerr(n - x)
        - bd0(x, n * p)
        - bd0(n - x, n * q)
    )

    lf = log(2 * pi) + log(x) + log1p(-x / n)
    return lc - 0.5 * lf


@jit(nopython=True)
def beta_pdf_fast(x: float, a: float, b: float) -> float:
    """
    Beta probability distribution. Translated and adapted from
    https://en.wikipedia.org/wiki/Beta_distribution, but calculated in the log
    domain.

    In R: plot(function(x) dbeta(x, shape1 = a, shape2 = b))

    See https://github.com/SurajGupta/r-source/blob/master/src/nmath/dbeta.c.
    - For lower.tail = TRUE and log.p = FALSE (the defaults), R_DT_0 means 0.
    - For log.p = FALSE (the default), R_D_val(x) means x.

    Original license:

    .. code-block:: none

        /*
         *  AUTHOR
         *    Catherine Loader, catherine@research.bell-labs.com.
         *    October 23, 2000.
         *
         *  Merge in to R:
         *	Copyright (C) 2000, The R Core Team
         *  Changes to case a, b < 2, use logs to avoid underflow
         *	Copyright (C) 2006-2014 The R Core Team
         *
         *  This program is free software; you can redistribute it and/or modify
         *  it under the terms of the GNU General Public License as published by
         *  the Free Software Foundation; either version 2 of the License, or
         *  (at your option) any later version.
         *
         *  This program is distributed in the hope that it will be useful,
         *  but WITHOUT ANY WARRANTY; without even the implied warranty of
         *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
         *  GNU General Public License for more details.
         *
         *  You should have received a copy of the GNU General Public License
         *  along with this program; if not, a copy is available at
         *  https://www.R-project.org/Licenses/
         *
         *
         *  DESCRIPTION
         *    Beta density,
         *                   (a+b-1)!     a-1       b-1
         *      p(x;a,b) = ------------ x     (1-x)
         *                 (a-1)!(b-1)!
         *
         *               = (a+b-1) dbinom(a-1; a+b-2,x)
         *
         *    The basic formula for the log density is thus
         *    (a-1) log x + (b-1) log (1-x) - lbeta(a, b)
         *    If either a or b <= 2 then 0 < lbeta(a, b) < 710 and so no
         *    term is large.  We use Loader's code only if both a and b > 2.
         */

    """  # noqa
    # logger.critical(f"beta_pdf_fast(x={x}, a={a}, b={b})")
    if a < 0 or b < 0:
        return NaN
    if x < 0 or x > 1:
        # PDF is zero elsewhere
        return 0.0

    # limit cases for (a,b), leading to point masses
    if a == 0 or b == 0 or isinf(a) or isinf(b):
        if a == 0 and b == 0:
            # point mass 1/2 at each of {0,1}
            return inf if x == 0 or x == 1 else 0
        if a == 0 or (a / b == 0):
            # point mass 1 at 0
            return inf if x == 0 else 0
        if b == 0 or b / a == 0:
            # point mass 1 at 1
            return inf if x == 1 else 0
        # remaining case:  a = b = Inf : point mass 1 at 1/2
        return inf if x == 0.5 else 0

    if x == 0:
        if a > 1:
            return 0
        if a < 1:
            return inf
        # a == 1
        return b

    if x == 1:
        if b > 1:
            return 0
        if b < 1:
            return inf
        # b == 1
        return a

    if a <= 2 or b <= 2:
        lbeta_ab = lgamma(a) + lgamma(b) - lgamma(a + b)
        # ... lbeta(a, b) in the R version
        lval = (a - 1) * log(x) + (b - 1) * log1p(-x) - lbeta_ab
    else:
        lval = log(a + b - 1) + dbinom_raw_log(a - 1, a + b - 2, x, 1 - x)
    return exp(lval)


# =============================================================================
# Helper functions: jit
# =============================================================================


def jit_integrand_function_with_args(
    integrand_function: Callable[[np.ndarray], float]
) -> LowLevelCallable:
    """
    Decorator to wrap a function that will be integrated by Scipy. See
    https://stackoverflow.com/questions/51109429/.

    carray:

    - Returns a Numpy array view over the data pointed to by ptr with the given
      shape, in C order.
    - https://numba.pydata.org/numba-doc/dev/reference/utils.html
    - Syntax: carray(ptr, shape, dtype=None).

    cfunc:

    - Decorator to compile a Python function into a C callback.
    - https://numba.pydata.org/numba-doc/dev/user/cfunc.html
    - Notation 1: @cfunc(return_type(arg1, arg2, ...))
    - Notation 2: @cfunc("return_type(arg1, arg2, ...)")

    CPointer:

    - Type class for pointers to other types.
    - Syntax: CPointer(dtype, addrspace=None).

    Scipy's quad() accepts either a Python function or a C callback wrapped in
    a ctypes callback object. This decorator converts the former to the latter.

    Specifically
    (https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html),
    quad accepts a scipy.LowLevelCallable with one of these signatures:

    .. code-block:: cpp

        double func(double x);
        double func(double x, void *user_data);
        double func(int n, double *xx);  // THIS ONE.
        double func(int n, double *xx, void *user_data);

    NOTE: "In the call forms with xx, n is the length of the xx array which
    contains xx[0] == x and the rest of the items are numbers contained in the
    args argument of quad."

    See specimen use below.

    """
    jitted_function = jit(integrand_function, nopython=True)

    @cfunc(float64(intc, CPointer(float64)))
    def wrapped(n: int, xx: CPointer(float64)) -> float64:
        args = carray(xx, n)
        return jitted_function(args)

    return LowLevelCallable(wrapped.ctypes)


def dummy_jit_integrand_function_with_args(
    integrand_function: Callable[[np.ndarray], float]
) -> Callable[..., float]:
    """
    Dummy version of jit_integrand_function_with_args, for debugging. Use this
    instead if, for example, you want to be able to use the Python logger.
    """

    def wrapped(*args: float) -> float:
        """
        When we use a plain Python function, Scipy's quad() will pass us
        arguments in *args format (x followed by the other arguments).

        When we use a LowLevelCallabel, quad() will pass us n and xx, which we
        convert to a Numpy array (see jit_integrand_function_with_args above).

        So here, we convert *args to a numpy array, so we can use the same
        underlying function.
        """
        return integrand_function(np.array(args, dtype=float))

    return wrapped


# =============================================================================
# Fast RPM: two choice
# =============================================================================


@jit_integrand_function_with_args
def rpm_integrand_twochoice(args: np.ndarray) -> float:
    """
    RPM integrand for a two-choice situation, for which we will calculate only
    one probability.

    Scipy's quad() function allows a generic user parameter array, which we can
    unpack. The first argument is x; the others are as we defined them.
    """
    (
        x,
        n_success_this,
        n_failure_this,
        n_success_other,
        n_failure_other,
    ) = args
    return beta_pdf_fast(
        x, n_success_this + 1, n_failure_this + 1
    ) * beta_cdf_fast(x, n_success_other + 1, n_failure_other + 1)


def rpm_probabilities_successes_failures_twochoice_fast(
    n_success_this: int,
    n_failure_this: int,
    n_success_other: int,
    n_failure_other: int,
) -> float:
    """
    Calculate the optimal choice probability for the first of two options in
    two-choice RPM.

    Curiously, copying rpm_probabilities_successes_failures from this library
    to user code, essentially unmodified, stopped a memory explosion (it looks
    like scipy is playing with docstrings, maybe?).

    It was still very slow and that relates to quad().

    Here we (a) only calculate one action (50% faster just from that!) and (b)
    use functions optimized using numba.jit.

    - https://stackoverflow.com/questions/68491563/numba-for-scipy-integration-and-interpolation
    - https://stackoverflow.com/questions/51109429/how-to-use-numba-to-perform-multiple-integration-in-scipy-with-an-arbitrary-numb

    Massively tedious optimization (translation from R's C code to Python) but
    it works very well.

    """  # noqa
    args = (n_success_this, n_failure_this, n_success_other, n_failure_other)
    # ... tuple, not numpy array, or we get "TypeError: only size-1 arrays can
    # be converted to Python scalars"

    # Integrate our function from 0 to 1:
    p_this = quad(rpm_integrand_twochoice, 0, 1, args=args)[0]
    # quad() returns a tuple. The first value is y, the integral. The second
    # is an estimate of the absolute error. There may be others.

    return p_this


# =============================================================================
# Fast RPM: generic
# =============================================================================


@jit_integrand_function_with_args
# @dummy_jit_integrand_function_with_args
def rpm_integrand_n_choice(args: np.ndarray) -> float:
    """
    RPM integrand for an arbitrary number of actions.
    """
    x = args[0]
    k = int(args[1])  # k is the number of actions
    current_action = int(args[2])  # zero-based index
    n_successes_plus_one = args[3 : k + 3]  # noqa: E203
    n_failures_plus_one = args[k + 3 :]  # noqa: E203

    r = beta_pdf_fast(
        x,
        n_successes_plus_one[current_action],
        n_failures_plus_one[current_action],
    )
    for j in range(k):
        if j == current_action:
            continue
        # So, for only the other actions:
        r *= beta_cdf_fast(x, n_successes_plus_one[j], n_failures_plus_one[j])
    return r


def rpm_probabilities_successes_failures_fast(
    n_successes: npt.ArrayLike, n_failures: npt.ArrayLike
) -> np.ndarray:
    """
    Fast version of rpm_probabilities_successes_failures().
    """
    # noinspection DuplicatedCode
    k = len(n_successes)  # k is the number of actions
    assert len(n_failures) == k
    assert np.all(np.greater_equal(n_successes, 0))
    assert np.all(np.greater_equal(n_failures, 0))
    p_choice = np.zeros(shape=[k])  # answer to be populated

    n_successes_plus_one = np.array(n_successes) + 1
    n_failures_plus_one = np.array(n_failures) + 1
    for i in range(k):  # for each action:
        args = tuple(
            np.concatenate(
                ([k, i], n_successes_plus_one, n_failures_plus_one),
            )
        )
        q = quad(rpm_integrand_n_choice, 0, 1, args=args)[0]
        p_choice[i] = q

    return p_choice
