#!/usr/bin/env python
# cardinal_pythonlib/parallel.py

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

**Parallel processing assistance functions.**

"""

from concurrent.futures import (
    Executor,
    FIRST_COMPLETED,
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    wait,
)
import logging
from itertools import islice
from typing import Callable, Iterable, Tuple

log = logging.getLogger(__name__)


def gen_parallel_results_efficiently(
    fn: Callable,
    *iterables: Iterable,
    max_workers: int = None,
    threaded: bool = False,
    verbose: bool = False,
    loglevel: int = logging.INFO,
) -> Iterable:
    """
    Memory-efficient way of using concurrent.futures.ProcessPoolExecutor, as
    per https://alexwlchan.net/2019/10/adventures-with-concurrent-futures/.
    The problem is that the normal method via e.g.
    ``ProcessPoolExecutor.map()`` creates large numbers of Future objects and
    runs out of memory; it doesn't scale to large (or infinite) inputs.

    Implemented 2020-04-19 with some tweaks to the original, and tested with
    Python 3.6.

    Note that there are also Python bug reports about this:

    - https://bugs.python.org/issue29842

      - and some duplicates of this

    - https://bugs.python.org/issue34168

    Args:
        fn:
            The function of interest to be run. A callable that will take as
            many arguments as there are passed iterables.
        iterables:
            Arguments to be sent ``fn``. For example, if you call
            ``parallelize_process_efficiently(fn, [a, b, c], [d, e, f])``
            then calls to ``fn`` will be ``fn(a, d)``, ``fn(b, e)``, and
            ``fn(c, f)``.
        max_workers:
            Maximum number of processes/threads at one time.
        threaded:
            Use threads? Otherwise, use processes.
        verbose:
            Report progress?
        loglevel
            If verbose, which loglevel to use?

    Yields:
        results from ``fn``, in no guaranteed order

    Note re ``itertools.islice``:

    .. code-block:: python

        from itertools import islice

        x = range(100)  # a range object; not an iterator

        print(list(islice(x, 10)))  # [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        print(list(islice(x, 10)))  # [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        y = zip(x)  # a generator; an iterator

        print(list(islice(y, 10)))  # [(0,), (1,), ..., (9,)]
        print(list(islice(y, 10)))  # [(10,), (11,), ..., (19,)]

        # ... with a zip() result, islice() continues where it left off.
        # Verified: this code does call the right number of subprocesses.
    """
    arggroups = zip(*iterables)  # an iterator of argument tuples
    n_submitted = 0
    executor_class = ThreadPoolExecutor if threaded else ProcessPoolExecutor

    def submit(executor_: Executor, args: Tuple) -> Future:
        if verbose:
            nonlocal n_submitted
            n_submitted += 1
            log.log(loglevel, f"Job {n_submitted}, submitting args: {args!r}")
        return executor_.submit(fn, *args)

    with executor_class(max_workers=max_workers) as executor:
        # Schedule the first N futures.  We don't want to schedule them all
        # at once, to avoid consuming excessive amounts of memory.
        futures = {
            submit(executor, args) for args in islice(arggroups, max_workers)
        }

        while futures:
            # Wait for the next future to complete.
            done, futures = wait(futures, return_when=FIRST_COMPLETED)

            for future in done:
                yield future.result()

            # Schedule the next set of futures.  We don't want more than N
            # futures in the pool at a time, to keep memory consumption down.
            for args in islice(arggroups, len(done)):
                futures.add(submit(executor, args))
