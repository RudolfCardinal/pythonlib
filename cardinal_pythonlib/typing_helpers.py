#!/usr/bin/env python
# cardinal_pythonlib/typing_helpers.py

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

**Unusual types for type hints.**

"""

from abc import abstractmethod
import csv
from typing import List


# =============================================================================
# csv.writer
# =============================================================================

class CSVWriterType(object):
    """
    Type hint for the result of ``csv.writer()``

    See https://stackoverflow.com/questions/51264355/how-to-type-annotate-object-returned-by-csv-writer
    """  # noqa

    @abstractmethod
    def writerow(self, row: List[str]) -> None:
        pass

    @abstractmethod
    def writerows(self, rows: List[List[str]]) -> None:
        pass

    @property
    @abstractmethod
    def dialect(self) -> csv.Dialect:
        pass
