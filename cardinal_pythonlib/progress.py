#!/usr/bin/env python
# cardinal_pythonlib/progress.py

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

**Counters etc. for visual display of progress.**

"""

import logging

log = logging.getLogger(__name__)


# =============================================================================
# Visuals
# =============================================================================


class ActivityCounter(object):
    """
    Simple class to report progress in a repetitive activity.
    """

    def __init__(
        self,
        activity: str,
        n_total: int = None,
        report_every: int = 1000,
        loglevel: int = logging.DEBUG,
    ) -> None:
        """
        Args:
            activity:
                Description of the repetitive activity being performed.
            n_total:
                If known, the total number of iterations required.
            report_every:
                Report progress every n operations.
            loglevel:
                Log level to use.
        """
        self.activity = activity
        self.count = 0
        self.n_total = n_total
        self.report_every = report_every
        self.loglevel = loglevel

    def tick(self) -> None:
        """
        Note a further occurrence, and report progress if required.
        """
        self.count += 1
        c = self.count
        n = self.n_total
        if c == 1 or c % self.report_every == 0 or c == n:
            if self.n_total is not None:
                of_n = f" of {n}"
            else:
                of_n = ""
            log.log(self.loglevel, f"{self.activity} {c}{of_n}")
