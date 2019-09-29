#!/usr/bin/env python
# cardinal_pythonlib/pyramid/compression.py

"""
===============================================================================

    Copyright (C) 2015-2019 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of CRATE.

    CRATE is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    CRATE is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with CRATE. If not, see <http://www.gnu.org/licenses/>.

===============================================================================

Compression functions.

"""

import logging

from pyramid.request import Request
from pyramid.response import Response
from pyramid.registry import Registry

from cardinal_pythonlib.pyramid.constants import PyramidHandlerType
from cardinal_pythonlib.pyramid.requests import (
    decompress_request,
    request_accepts_gzip,
)

log = logging.getLogger(__name__)


# =============================================================================
# Pyramid gzip compression tween
# =============================================================================

class CompressionTweenFactory(object):
    """
    Makes a Pyramid tween that (a) detects incoming compression and
    uncompresses requests; (b) applies compression to responses if the
    requestor will accept this.

    See:

    - https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/hooks.html
    - https://docs.pylonsproject.org/projects/pyramid/en/latest/api/request.html
    - https://docs.pylonsproject.org/projects/pyramid/en/latest/api/response.html
    """  # noqa

    def __init__(self, handler: PyramidHandlerType,
                 registry: Registry) -> None:
        self.handler = handler
        self.registry = registry

    def __call__(self, request: Request) -> Response:
        # 1. Pre-processing, if required.
        decompress_request(request)
        # 2. Call the rest of the application:
        response = self.handler(request)  # type: Response
        # 3. Post-processing:
        if request_accepts_gzip(request):
            response.encode_content("gzip")
            # Only gzip is supported directly by webob, but it's a good choice.
        # 4. Done
        return response
