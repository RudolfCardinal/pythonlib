#!/usr/bin/env python
# cardinal_pythonlib/probability.py

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

**Miscellaneous probability functions.**

"""

import math


# =============================================================================
# Basic maths
# =============================================================================

def ln(x: float) -> float:
    """
    Version of :func:`math.log` that treats log(0) as ``-inf``, rather than
    crashing with ``ValueError: math domain error``.

    Args:
        x: parameter

    Returns:
        float: ln(x), the natural logarithm of x

    See
    https://stackoverflow.com/questions/42980201/logarithm-of-zero-in-python.
    """
    return math.log(x) if x != 0 else -math.inf


def log10(x: float) -> float:
    """
    Version of :func:`math.log10` that treats log(0) as ``-inf``, rather than
    crashing with ``ValueError: math domain error``.

    Args:
        x: parameter

    Returns:
        float: log10(x), the logarithm to base 10 of x

    See
    https://stackoverflow.com/questions/42980201/logarithm-of-zero-in-python.
    """
    return math.log10(x) if x != 0 else -math.inf


# =============================================================================
# Basic probability
# =============================================================================

def odds_from_probability(p: float) -> float:
    r"""
    Returns odds, given a probability.

    .. math::

        o = \frac{p}{1 - p}

    Args:
        p: probability

    Returns:
        float: odds
    """
    return p / (1 - p)


def probability_from_odds(odds: float) -> float:
    r"""
    Returns a probability, given odds.

    .. math::

        o &= \frac{p}{1 - p}  \\
        o (1 - p) &= p  \\
        o - op &= p  \\
        o &= p + op  \\
        o &= p(1 + o)  \\
        p &= \frac{o}{1 + o}

    Args:
        odds: odds

    Returns:
        float: probability
    """
    return odds / (1 + odds)


def probability_from_log_prob(log_p: float) -> float:
    """
    Returns a probability from a log probability.

    Args:
        log_p: ln(p); natural log of p

    Returns:
        float: p
    """
    return math.exp(log_p)


def probability_from_log_odds(log_odds: float) -> float:
    """
    Returns a probability from a log odds.

    Args:
        log_odds: ln(o); natural log of o

    Returns:
        float: p
    """
    odds = math.exp(log_odds)
    return probability_from_odds(odds)


def log_probability_from_log_odds(log_odds: float) -> float:
    r"""
    No obvious quick form for this:

    .. math::

        o &= \frac{p}{1 - p}  \\

        \log o &= \log p - \log (1 - p)  \\

    Args:
        log_odds: ln(o); natural log of o

    Returns:
        float: ln(p)

    """
    p = probability_from_log_odds(log_odds)
    return ln(p)


def log_odds_from_probability(p: float) -> float:
    """
    Returns log ods from a probability.

    Args:
        p: probability

    Returns:
        float: ln(odds)

    See

    - https://wiki.lesswrong.com/wiki/Odds_ratio
    - https://wiki.lesswrong.com/wiki/Log_odds
    """
    return ln(odds_from_probability(p))


def log_odds_from_1_in_n(n: float) -> float:
    r"""
    If the chance of something occurring are 1 in n, then its probability is
    :math:`1/n`, and its odds are :math:`\frac{1}{n - 1}`. This function
    returns the log of those odds.

    Args:
        n: ``n``, as above

    Returns:
        float: :math:`\ln \frac{1}{n - 1} = \ln 1 - \ln (n - 1) = -\ln(n - 1)`
    """
    return -ln(n - 1)


# =============================================================================
# Bayesian update rules
# =============================================================================

def bayes_posterior(prior: float, likelihood: float,
                    marginal_likelihood: float) -> float:
    r"""
    Returns P(H | D), the posterior probability of hypothesis H, given data D.

    Args:
        prior:
            P(H), the prior belief in H
        likelihood:
            P(D | H), the probability of observing D given H
        marginal_likelihood:
            P(D), the probability of observing D; also called evidence or model
            evidence.

    Returns:
        float: P(H | D), the probability of H given D.

    Bayes' rule:

    .. math::

        P(A | B) P(B) = P(B | A) P(A) = P(A \land B)

        P(H | D) = \frac{ P(D | H) \cdot P(H) }{ P(D) }

        \text{posterior} =
            \frac
            { \text{likelihood} \cdot \text{prior} }
            { \text{marginal likelihood} }

    """
    return likelihood * prior / marginal_likelihood


def log_bayes_posterior(log_prior: float, log_likelihood: float,
                        log_marginal_likelihood: float) -> float:
    r"""
    Exactly equivalent to :func:`bayes_posterior`, but using log probability.

    Args:
        log_prior: :math:`\log P(H)`
        log_likelihood: :math:`\log P(D | H)`
        log_marginal_likelihood: :math:`\log P(D)`

    Returns:
        float: :math:`\log P(H | D)`
    """
    return log_likelihood + log_prior - log_marginal_likelihood


def posterior_odds(prior_odds: float,
                   likelihood_ratio: float) -> float:
    r"""
    Returns the posterior odds for a hypothesis, given the prior odds and the
    likelihood ratio.

    .. math::

        P(A | B) &= P(B | A) \frac{ P(A) }{ P(B) }  \\

        P(\neg A | B) &= P(B | \neg A) \frac{ P(\neg A) }{ P(B) }  \\

        \frac{ P(A | B) }{ P(\neg A | B) } &=
            \frac{ P(B | A) }{ P(B | \neg A) }
            \frac{ P(A) }{ P(\neg A) }  \\

        \text{posterior odds} &= \text{likelihood ratio} \cdot
                                 \text{prior odds}

    Args:
        prior_odds:
            prior odds, :math:`\frac{ P(A) }{ P(\neg A) }`
        likelihood_ratio:
            likelihood ratio, :math:`\frac{ P(B | A) }{ P(B | \neg A) }`

    Returns:
        float: posterior odds, :math:`\frac{ P(A | B) }{ P(\neg A | B) }`

    e.g. https://wiki.lesswrong.com/wiki/Odds_ratio

    """
    return likelihood_ratio * prior_odds


def log_posterior_odds(log_prior_odds: float,
                       log_likelihood_ratio: float) -> float:
    r"""
    Exactly as for :func:`posterior_odds`, but with log odds.
    """
    return log_likelihood_ratio + log_prior_odds


def log_likelihood_ratio_from_p(p_d_given_h: float,
                                p_d_given_not_h: float) -> float:
    r"""
    Returns
    
    .. math::
    
        \ln \frac{ P(D | H) }{ P(D | \neg H) } = 
            \ln P(D | H) - \ln P(D | \neg H)

    Args:
        p_d_given_h: :math:`P(D | H)`
        p_d_given_not_h: :math:`P(D | \neg H)`

    Returns:
        float: log likelihood ratio, as above

    """  # noqa
    return ln(p_d_given_h) - ln(p_d_given_not_h)


def log_posterior_odds_from_pdh_pdnh(log_prior_odds: float,
                                     p_d_given_h: float,
                                     p_d_given_not_h: float) -> float:
    r"""
    Calculates posterior odds.

    Args:
        log_prior_odds:
            log prior odds of H, :math:`ln(\frac{ P(H) }{ P(\neg H) })`
        p_d_given_h:
            :math:`P(D | H)`
        p_d_given_not_h:
            :math:`P(D | \neg H)`

    Returns:
        float:
            posterior odds of H, :math:`ln(\frac{ P(H | D) }{ P(\neg H | D) })`

    """
    log_lr = log_likelihood_ratio_from_p(
        p_d_given_h=p_d_given_h,
        p_d_given_not_h=p_d_given_not_h
    )
    return log_posterior_odds(
        log_prior_odds=log_prior_odds,
        log_likelihood_ratio=log_lr
    )


def log_posterior_odds_from_bool_d_pdh_pdnh(log_prior_odds: float,
                                            d: bool,
                                            p_d_given_h: float,
                                            p_d_given_not_h: float) -> float:
    r"""
    Calculates posterior odds.

    Args:
        log_prior_odds:
            log prior odds of H, :math:`ln(\frac{ P(H) }{ P(\neg H) })`
        d:
            whether D is true or not
        p_d_given_h:
            :math:`P(D | H)`
        p_d_given_not_h:
            :math:`P(D | \neg H)`

    Returns:
        float:
            posterior odds of H, :math:`ln(\frac{ P(H | D) }{ P(\neg H | D) })`

    """
    if d:
        # D is true
        log_lr = log_likelihood_ratio_from_p(
            p_d_given_h=p_d_given_h,
            p_d_given_not_h=p_d_given_not_h
        )
    else:
        # not-D is true
        p_not_d_given_h = 1 - p_d_given_h
        p_not_d_given_not_h = 1 - p_d_given_not_h
        log_lr = log_likelihood_ratio_from_p(
            p_d_given_h=p_not_d_given_h,
            p_d_given_not_h=p_not_d_given_not_h
        )
    return log_posterior_odds(
        log_prior_odds=log_prior_odds,
        log_likelihood_ratio=log_lr
    )
