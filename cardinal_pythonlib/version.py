#!/usr/bin/env python
# cardinal_pythonlib/version.py

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
"""

VERSION = '1.0.8'
# Use semantic versioning: http://semver.org/

RECENT_VERSION_HISTORY = """

First started in 2009.

- 0.2.7, 2017-04-28
  Fixed bug in rnc_extract_text that was using get_file_contents() as a
  converter when it wasn't accepting generic **kwargs; now it is.
  
- 0.2.8, 2017-04-28
  Fixed DOCX table processing bug, in docx_process_table().
  
- 0.2.10, 2017-04-29
  Text fetch (for converters) was returning bytes, not str; fixed.

- 0.2.11, 2017-04-29
  Encoding auto-detection for text extraction from files.

- 0.2.12 to 0.2.13, 2017-05-02
  More file types support for simple text extraction.
  Better encoding support.
  
- 1.0.0, 2017-08-05.
  Consolidation of common functions from multiple projects to reduce code
  duplication. Some modules renamed.
  
- 1.0.1, 2017-08-14
  PyPI/setup.py bugfix (not all subpackages were uploaded).

- 1.0.2, 2017-08-20 onwards
  Metaclass functions added.
  Extensions to SQLAlchemy utility functions.
  
- 1.0.3, 2017-10-18.
  Several small changes for CamCOPS.
  
- ... to 1.0.8, 2017-11-29.
  Similarly.

"""
