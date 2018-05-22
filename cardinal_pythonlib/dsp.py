#!/usr/bin/env python
# cardinal_pythonlib/dsp.py

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

Digital signal processing functions

"""

from typing import List, Union

import numpy as np
from scipy.signal import firwin, iirnotch, lfilter

FLOATS_TYPE = Union[List[float], np.ndarray]


# =============================================================================
# Filters
# =============================================================================

def normalized_frequency(f: float, sampling_freq: float) -> float:
    return f / (sampling_freq / 2.0)
    # e.g. see https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.iirnotch.html  # noqa
    # Principle:
    # - if maximum frequency of interest is f, then you should sample at the
    #   Nyquist frequency of 2f;
    # - conversely, if you sample at 2f, then the normalized frequency is the
    #   range [0, 1] for the frequency range [0, f].


def lowpass_filter(data: FLOATS_TYPE,
                   sampling_freq_hz: float,
                   cutoff_freq_hz: float,
                   numtaps: int) -> FLOATS_TYPE:
    """
    Apply a low-pass filter to the data.
    Returns filtered data.

    Note: number of filter taps = filter order + 1
    """
    coeffs = firwin(
        numtaps=numtaps,
        cutoff=normalized_frequency(cutoff_freq_hz, sampling_freq_hz),
        pass_zero=True
    )  # coefficients of a finite impulse response (FIR) filter using window method  # noqa
    filtered_data = lfilter(b=coeffs, a=1.0, x=data)
    return filtered_data


def highpass_filter(data: FLOATS_TYPE,
                    sampling_freq_hz: float,
                    cutoff_freq_hz: float,
                    numtaps: int) -> FLOATS_TYPE:
    """
    Apply a high-pass filter to the data.
    Returns filtered data.
    """
    coeffs = firwin(
        numtaps=numtaps,
        cutoff=normalized_frequency(cutoff_freq_hz, sampling_freq_hz),
        pass_zero=False
    )
    filtered_data = lfilter(b=coeffs, a=1.0, x=data)
    return filtered_data


def bandpass_filter(data: FLOATS_TYPE,
                    sampling_freq_hz: float,
                    lower_freq_hz: float,
                    upper_freq_hz: float,
                    numtaps: int) -> FLOATS_TYPE:
    """
    Apply a band-pass filter to the data.
    Returns filtered data.
    """
    f1 = normalized_frequency(lower_freq_hz, sampling_freq_hz)
    f2 = normalized_frequency(upper_freq_hz, sampling_freq_hz)
    coeffs = firwin(
        numtaps=numtaps,
        cutoff=[f1, f2],
        pass_zero=False
    )
    filtered_data = lfilter(b=coeffs, a=1.0, x=data)
    return filtered_data


def notch_filter(data: FLOATS_TYPE,
                 sampling_freq_hz: float,
                 notch_freq_hz: float,
                 quality_factor: float) -> FLOATS_TYPE:
    """
    Design and use a notch (band reject) filter to filter the data.
    Returns filtered data.
    """
    b, a = iirnotch(
        w0=normalized_frequency(notch_freq_hz, sampling_freq_hz),
        Q=quality_factor
    )
    filtered_data = lfilter(b=b, a=a, x=data)
    return filtered_data
