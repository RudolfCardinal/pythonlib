#!/usr/bin/env python
# cardinal_pythonlib/betweendict.py

"""
===============================================================================
    Copyright (C) 2009-2017 Rudolf Cardinal (rudolf@pobox.com).

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
"""

from typing import Dict


# =============================================================================
# Range dictionary for comparisons
# =============================================================================

class BetweenDict(dict):
    # Various alternatives:
    # http://joshuakugler.com/archives/30-BetweenDict,-a-Python-dict-for-value-ranges.html  # noqa
    #   ... NB has initialization default argument bug
    # https://pypi.python.org/pypi/rangedict/0.1.5
    # http://stackoverflow.com/questions/30254739/is-there-a-library-implemented-rangedict-in-python  # noqa
    INVALID_MSG_TYPE = "Key must be an iterable with length 2"
    INVALID_MSG_VALUE = "First element of key must be less than second element"

    # noinspection PyMissingConstructor
    def __init__(self, d: Dict = None) -> None:
        d = d or {}
        for k, v in d.items():
            self[k] = v

    def __getitem__(self, key):
        for k, v in self.items():
            if k[0] <= key < k[1]:
                return v
        raise KeyError("Key '{}' is not in any ranges".format(key))

    def __setitem__(self, key, value):
        try:
            if len(key) != 2:
                raise ValueError(self.INVALID_MSG_TYPE)
        except TypeError:
            raise TypeError(self.INVALID_MSG_TYPE)
        if key[0] < key[1]:
            super().__setitem__((key[0], key[1]), value)
        else:
            raise RuntimeError(self.INVALID_MSG_VALUE)

    def __contains__(self, key):
        try:
            # noinspection PyStatementEffect
            self[key]
            return True
        except KeyError:
            return False
