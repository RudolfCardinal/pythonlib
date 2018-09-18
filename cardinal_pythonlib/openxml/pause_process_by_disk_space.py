#!/usr/bin/env python3
# cardinal_pythonlib/openxml/pause_process_by_disk_space.py

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

**Pauses and resumes a process by disk space; LINUX ONLY.**

"""

from argparse import ArgumentParser
import logging
import shutil
import subprocess
import sys
from time import sleep

from cardinal_pythonlib.logs import (
    BraceStyleAdapter,
    main_only_quicksetup_rootlogger,
)
from cardinal_pythonlib.sizeformatter import human2bytes, sizeof_fmt

log = BraceStyleAdapter(logging.getLogger(__name__))


def is_running(process_id: int) -> bool:
    """
    Uses the Unix ``ps`` program to see if a process is running.
    """
    pstr = str(process_id)
    encoding = sys.getdefaultencoding()
    s = subprocess.Popen(["ps", "-p", pstr], stdout=subprocess.PIPE)
    for line in s.stdout:
        strline = line.decode(encoding)
        if pstr in strline:
            return True
    return False


def main() -> None:
    """
    Command-line handler for the ``pause_process_by_disk_space`` tool.
    Use the ``--help`` option for help.
    """
    parser = ArgumentParser(
        description="Pauses and resumes a process by disk space; LINUX ONLY."
    )
    parser.add_argument(
        "process_id", type=int,
        help="Process ID."
    )
    parser.add_argument(
        "--path", required=True,
        help="Path to check free space for (e.g. '/')"
    )
    parser.add_argument(
        "--pause_when_free_below", type=str, required=True,
        help="Pause process when free disk space below this value (in bytes "
             "or as e.g. '50G')"
    )
    parser.add_argument(
        "--resume_when_free_above", type=str, required=True,
        help="Resume process when free disk space above this value (in bytes "
             "or as e.g. '70G')"
    )
    parser.add_argument(
        "--check_every", type=int, required=True,
        help="Check every n seconds (where this is n)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Verbose output"
    )
    args = parser.parse_args()
    main_only_quicksetup_rootlogger(
        level=logging.DEBUG if args.verbose else logging.INFO)

    minimum = human2bytes(args.pause_when_free_below)
    maximum = human2bytes(args.resume_when_free_above)
    path = args.path
    process_id = args.process_id
    period = args.check_every
    pause_args = ["kill", "-STOP", str(process_id)]
    resume_args = ["kill", "-CONT", str(process_id)]

    assert minimum < maximum, "Minimum must be less than maximum"

    log.info(
        "Starting: controlling process {proc}; "
        "checking disk space every {period} s; "
        "will pause when free space on {path} is less than {minimum} and "
        "resume when free space is at least {maximum}; "
        "pause command will be {pause}; "
        "resume command will be {resume}.".format(
            proc=process_id,
            period=period,
            path=path,
            minimum=sizeof_fmt(minimum),
            maximum=sizeof_fmt(maximum),
            pause=pause_args,
            resume=resume_args,
        ))
    log.debug("Presuming that the process is RUNNING to begin with.")

    paused = False
    while True:
        if not is_running(process_id):
            log.info("Process {} is no longer running", process_id)
            sys.exit(0)
        space = shutil.disk_usage(path).free
        log.debug("Disk space on {} is {}", path, sizeof_fmt(space))
        if space < minimum and not paused:
            log.info("Disk space down to {}: pausing process {}",
                     sizeof_fmt(space), process_id)
            subprocess.check_call(pause_args)
            paused = True
        elif space >= maximum and paused:
            log.info("Disk space up to {}: resuming process {}",
                     sizeof_fmt(space), process_id)
            subprocess.check_call(resume_args)
            paused = False
        log.debug("Sleeping for {} seconds...", period)
        sleep(period)


if __name__ == '__main__':
    main()
