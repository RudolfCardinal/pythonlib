#!/usr/bin/env python
# cardinal_pythonlib/version.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.


VERSION = '0.2.7'
# Use semantic versioning: http://semver.org/

RECENT_VERSION_HISTORY = """

- 0.2.7, 2017-04-28
  Fixed bug in rnc_extract_text that was using get_file_contents() as a
  converter when it wasn't accepting generic **kwargs; now it is.

"""