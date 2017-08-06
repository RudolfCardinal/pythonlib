#!/usr/bin/env python
# cardinal_pythonlib/network.py

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

Network support functions.

NOTES:
- ping requires root to create ICMP sockets in Linux
- the /bin/ping command doesn't need root (because it has the setuid bit set)
- For Linux, it's best to use the system ping.

http://stackoverflow.com/questions/2953462/pinging-servers-in-python
http://stackoverflow.com/questions/316866/ping-a-site-in-python

- Note that if you want a sub-second timeout, things get trickier.
  One option is fping.
"""

import subprocess
import sys


def ping(hostname: str, timeout_s: int = 5) -> bool:
    if sys.platform == "win32":
        timeout_ms = timeout_s * 1000
        args = [
            "ping",
            hostname,
            "-n", "1",  # ping count
            "-w", str(timeout_ms),  # timeout
        ]
    elif sys.platform.startswith('linux'):
        args = [
            "ping",
            hostname,
            "-c", "1",  # ping count
            "-w", str(timeout_s),  # timeout
        ]
    else:
        raise AssertionError("Don't know how to ping on this operating system")
    proc = subprocess.Popen(args,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    retcode = proc.returncode
    return retcode == 0  # zero success, non-zero failure
