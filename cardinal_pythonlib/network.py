#!/usr/bin/env python
# cardinal_pythonlib/network.py

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

**Network support functions.**

NOTES:

- ``ping`` requires root authority to create ICMP sockets in Linux
- the ``/bin/ping`` command doesn't need prior root authority (because it has
  the setuid bit set)
- For Linux, it's therefore best to use the system ``ping``.

https://stackoverflow.com/questions/2953462/pinging-servers-in-python
https://stackoverflow.com/questions/316866/ping-a-site-in-python

- Note that if you want a sub-second timeout, things get trickier.
  One option is ``fping``.

"""

import os
import ssl
import subprocess
import sys
import tempfile
from typing import BinaryIO, Dict, Generator, Iterable
import urllib.request

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Ping
# =============================================================================

def ping(hostname: str, timeout_s: int = 5) -> bool:
    """
    Pings a host, using OS tools.

    Args:
        hostname: host name or IP address
        timeout_s: timeout in seconds

    Returns:
        was the ping successful?

    """
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


# =============================================================================
# Download things
# =============================================================================

def download(url: str,
             filename: str,
             skip_cert_verify: bool = True,
             headers: Dict[str, str] = None) -> None:
    """
    Downloads a URL to a file.

    Args:
        url:
            URL to download from
        filename:
            file to save to
        skip_cert_verify:
            skip SSL certificate check?
        headers:
            request headers (if not specified, a default will be used that
            mimics Mozilla 5.0 to avoid certain HTTP 403 errors)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0'
    } if headers is None else headers
    log.info("Downloading from {} to {}", url, filename)

    # urllib.request.urlretrieve(url, filename)
    # ... sometimes fails (e.g. downloading
    # https://www.openssl.org/source/openssl-1.1.0g.tar.gz under Windows) with:
    # ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:777)  # noqa
    # ... due to this certificate root problem (probably because OpenSSL
    #     [used by Python] doesn't play entirely by the same rules as others?):
    # https://stackoverflow.com/questions/27804710
    # So:

    # Patching this by faking a browser request by adding User-Agent to request
    # headers, using this as example:
    # https://stackoverflow.com/questions/42863240/how-to-get-round-the-http-error-403-forbidden-with-urllib-request-using-python  # noqa

    ctx = ssl.create_default_context()  # type: ssl.SSLContext
    if skip_cert_verify:
        log.debug("Skipping SSL certificate check for " + url)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    page = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(page, context=ctx) as u, \
            open(filename, 'wb') as f:
        f.write(u.read())


# =============================================================================
# Generators
# =============================================================================

def gen_binary_files_from_urls(
        urls: Iterable[str],
        on_disk: bool = False,
        show_info: bool = True) -> Generator[BinaryIO, None, None]:
    """
    Generate binary files from a series of URLs (one per URL).

    Args:
        urls: iterable of URLs
        on_disk: if ``True``, yields files that are on disk (permitting
            random access); if ``False``, yields in-memory files (which will
            not permit random access)
        show_info: show progress to the log?

    Yields:
        files, each of type :class:`BinaryIO`

    """
    for url in urls:
        if on_disk:
            # Necessary for e.g. zip processing (random access)
            with tempfile.TemporaryDirectory() as tmpdir:
                filename = os.path.join(tmpdir, "tempfile")
                download(url=url, filename=filename)
                with open(filename, 'rb') as f:
                    yield f
        else:
            if show_info:
                log.info("Reading from URL: {}", url)
            with urllib.request.urlopen(url) as f:
                yield f
        if show_info:
            log.info("... finished reading from URL: {}", url)
