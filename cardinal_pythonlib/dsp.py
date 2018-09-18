#!/usr/bin/env python
# cardinal_pythonlib/dsp.py

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

**Digital signal processing functions.**

"""

from typing import List, Union

import numpy as np
from scipy.signal import firwin, iirnotch, lfilter

FLOATS_TYPE = Union[List[float], np.ndarray]


# =============================================================================
# Filters
# =============================================================================

def normalized_frequency(f: float, sampling_freq: float) -> float:
    """
    Returns a normalized frequency:

    Args:
        f: frequency :math:`f`
        sampling_freq: sampling frequency :math:`f_s`

    Returns:
        normalized frequency

            .. math::

                f_n = f / (f_s / 2)
                
    Principles:
    
    - if maximum frequency of interest is :math:`f`, then you should sample at
      the Nyquist rate of :math:`2f`;
    - if you sample at :math:`f_s`, then the maximum frequency is
      the Nyquist frequency :math:`0.5 f_s`
    - if you sample at :math:`2f`, then the normalized frequency is
      the range :math:`[0, 1]` for the frequency range :math:`[0, f]`.
    - e.g. see https://en.wikipedia.org/wiki/Nyquist_frequency,
      https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.iirnotch.html

    """  # noqa
    return f / (sampling_freq / 2.0)


def lowpass_filter(data: FLOATS_TYPE,
                   sampling_freq_hz: float,
                   cutoff_freq_hz: float,
                   numtaps: int) -> FLOATS_TYPE:
    """
    Apply a low-pass filter to the data.

    Args:
        data: time series of the data
        sampling_freq_hz: sampling frequency :math:`f_s`, in Hz
            (or other consistent units)
        cutoff_freq_hz: filter cutoff frequency in Hz
            (or other consistent units)
        numtaps: number of filter taps

    Returns:
        filtered data

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

    Args:
        data: time series of the data
        sampling_freq_hz: sampling frequency :math:`f_s`, in Hz
            (or other consistent units)
        cutoff_freq_hz: filter cutoff frequency in Hz
            (or other consistent units)
        numtaps: number of filter taps

    Returns:
        filtered data

    Note: number of filter taps = filter order + 1
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

    Args:
        data: time series of the data
        sampling_freq_hz: sampling frequency :math:`f_s`, in Hz
            (or other consistent units)
        lower_freq_hz: filter cutoff lower frequency in Hz
            (or other consistent units)
        upper_freq_hz: filter cutoff upper frequency in Hz
            (or other consistent units)
        numtaps: number of filter taps

    Returns:
        filtered data

    Note: number of filter taps = filter order + 1
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

    Args:
        data: time series of the data
        sampling_freq_hz: sampling frequency :math:`f_s`, in Hz
            (or other consistent units)
        notch_freq_hz: notch frequency, in Hz
            (or other consistent units)
        quality_factor: notch filter quality factor, :math:`Q`

    Returns:
        filtered data
    """
    b, a = iirnotch(
        w0=normalized_frequency(notch_freq_hz, sampling_freq_hz),
        Q=quality_factor
    )
    filtered_data = lfilter(b=b, a=a, x=data)
    return filtered_data
