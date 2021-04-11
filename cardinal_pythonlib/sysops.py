#!/usr/bin/env python
# cardinal_pythonlib/sysops.py

"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

**Simple system operations.**

"""

import logging
import os
import sys
from typing import NoReturn

log = logging.getLogger(__name__)


EXIT_FAILURE = 1
EXIT_SUCCESS = 0


def die(msg: str,
        log_level: int = logging.CRITICAL,
        exit_code: int = EXIT_FAILURE) -> NoReturn:
    """
    Prints a message and hard-exits the program.

    Args:
        msg: message
        log_level: log level to use
        exit_code: exit code (errorlevel)
    """
    log.log(level=log_level, msg=msg)
    sys.exit(exit_code)


def get_envvar_or_die(envvar: str,
                      log_level: int = logging.CRITICAL,
                      exit_code: int = EXIT_FAILURE) -> str:
    """
    Returns the value of an environment variable.
    If it is unset or blank, complains and hard-exits the program.

    Args:
        envvar: environment variable name
        log_level: log level to use for failure
        exit_code: exit code (errorlevel) for failure

    Returns:
        str: the value of the environment variable
    """
    value = os.environ.get(envvar)
    if not value:
        die(f"Must set environment variable {envvar}",
            log_level=log_level, exit_code=exit_code)
    return value
