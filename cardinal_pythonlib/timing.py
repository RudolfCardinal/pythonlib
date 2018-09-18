#!/usr/bin/env python
# cardinal_pythonlib/timing.py

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

**Timers for performance tuning.**

"""

from collections import OrderedDict
import datetime
import logging

from cardinal_pythonlib.datetimefunc import get_now_utc_pendulum
from cardinal_pythonlib.logs import BraceStyleAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


class MultiTimer(object):
    """
    Mutually exclusive timing of a set of events.

    Maintains a start count and times for a set of named timers.

    See example in :class:`MultiTimerContext`.
    """
    def __init__(self, start: bool = True) -> None:
        """
        Args:
            start: start the timer immediately?
        """
        self._timing = start
        self._overallstart = get_now_utc_pendulum()
        self._starttimes = OrderedDict()  # name: start time
        self._totaldurations = OrderedDict()  # name: duration
        self._count = OrderedDict()  # name: count
        self._stack = []  # list of names

    def reset(self) -> None:
        """
        Reset the timers.
        """
        self._overallstart = get_now_utc_pendulum()
        self._starttimes.clear()
        self._totaldurations.clear()
        self._count.clear()
        self._stack.clear()

    def set_timing(self, timing: bool, reset: bool = False) -> None:
        """
        Manually set the ``timing`` parameter, and optionally reset the timers.

        Args:
            timing: should we be timing?
            reset: reset the timers?

        """
        self._timing = timing
        if reset:
            self.reset()

    def start(self, name: str, increment_count: bool = True) -> None:
        """
        Start a named timer.

        Args:
            name: name of the timer
            increment_count: increment the start count for this timer

        """
        if not self._timing:
            return
        now = get_now_utc_pendulum()

        # If we were already timing something else, pause that.
        if self._stack:
            last = self._stack[-1]
            self._totaldurations[last] += now - self._starttimes[last]

        # Start timing our new thing
        if name not in self._starttimes:
            self._totaldurations[name] = datetime.timedelta()
            self._count[name] = 0
        self._starttimes[name] = now
        if increment_count:
            self._count[name] += 1
        self._stack.append(name)

    def stop(self, name: str) -> None:
        """
        Stop a named timer.

        Args:
            name: timer to stop
        """
        if not self._timing:
            return
        now = get_now_utc_pendulum()

        # Validity check
        if not self._stack:
            raise AssertionError("MultiTimer.stop() when nothing running")
        if self._stack[-1] != name:
            raise AssertionError(
                "MultiTimer.stop({}) when {} is running".format(
                    repr(name), repr(self._stack[-1])))

        # Finish what we were asked to
        self._totaldurations[name] += now - self._starttimes[name]
        self._stack.pop()

        # Now, if we were timing something else before we started "name",
        # resume...
        if self._stack:
            last = self._stack[-1]
            self._starttimes[last] = now

    def report(self) -> None:
        """
        Finish and report to the log.
        """
        while self._stack:
            self.stop(self._stack[-1])
        now = get_now_utc_pendulum()
        grand_total = datetime.timedelta()
        overall_duration = now - self._overallstart
        for name, duration in self._totaldurations.items():
            grand_total += duration

        log.info("Timing summary:")
        summaries = []
        for name, duration in self._totaldurations.items():
            n = self._count[name]
            total_sec = duration.total_seconds()
            mean = total_sec / n if n > 0 else None

            summaries.append({
                'total': total_sec,
                'description': (
                    "- {}: {:.3f} s ({:.2f}%, n={}, mean={:.3f}s)".format(
                        name,
                        total_sec,
                        (100 * total_sec / grand_total.total_seconds()),
                        n,
                        mean)),
            })
        summaries.sort(key=lambda x: x['total'], reverse=True)
        for s in summaries:
            # noinspection PyTypeChecker
            log.info(s["description"])
        if not self._totaldurations:
            log.info("<no timings recorded>")

        unmetered = overall_duration - grand_total
        log.info("Unmetered time: {:.3f} s ({:.2f}%)".format(
            unmetered.total_seconds(),
            100 * unmetered.total_seconds() / overall_duration.total_seconds()
        ))
        log.info("Total time: {:.3f} s".format(grand_total.total_seconds()))


class MultiTimerContext(object):
    """
    Context manager for :class:`MultiTimer`.

    Example:

    .. code-block:: python

        import logging
        from time import sleep
        from cardinal_pythonlib.timing import MultiTimer, MultiTimerContext

        timer = MultiTimer(start=True)

        def f2():
            with MultiTimerContext(timer, "f2"):
                print("starting f2")
                sleep(1)
                print("finishing f2")

        def f1():
            with MultiTimerContext(timer, "f1"):
                print("starting f1")
                sleep(0.25)
                f2()
                f2()
                print("finishing f1")

        logging.basicConfig(level=logging.DEBUG)
        f1()
        timer.report()

    """
    def __init__(self, multitimer: MultiTimer, name: str) -> None:
        """
        Args:
            multitimer: :class:`MultiTimer` to use
            name: name of timer to start as we enter, and stop as we exit
        """
        self.timer = multitimer
        self.name = name

    def __enter__(self):
        self.timer.start(self.name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.timer.stop(self.name)


# Optional global instance, for convenience.
# In a multithreading environment, MAKE YOUR OWN INSTANCES of MultiTimer().
timer = MultiTimer(start=False)
