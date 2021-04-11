#!/usr/bin/env python
# cardinal_pythonlib/pyramid/compression.py

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

Compression functions.

"""

import logging

# noinspection PyUnresolvedReferences
from pyramid.request import Request
# noinspection PyUnresolvedReferences
from pyramid.response import Response
# noinspection PyUnresolvedReferences
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
