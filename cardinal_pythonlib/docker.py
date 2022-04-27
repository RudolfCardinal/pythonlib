#!/usr/bin/env python
# cardinal_pythonlib/docker.py

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

**Support functions for Docker.**
"""

import os


def running_under_docker() -> bool:
    """
    Are we running inside a Docker container?

    As per
    https://stackoverflow.com/questions/43878953/how-does-one-detect-if-one-is-running-within-a-docker-container-within-python
    ... but without leaving a file open.
    """  # noqa
    # 1. Does /.dockerenv exist?
    if os.path.exists("/.dockerenv"):
        return True
    # 2. Is there a line containing "docker" in /proc/self/cgroup?
    path = "/proc/self/cgroup"
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                if "docker" in line:
                    return True
    return False
