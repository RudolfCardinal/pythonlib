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
from typing import Any, List, Optional, Sequence, Type, Union


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


class Pep249DatabaseCursorType(object):
    """
    Type hint for a database cursor compliant with PEP 249. See
    https://www.python.org/dev/peps/pep-0249/#cursor-objects

    Example, as per https://docs.python.org/3.6/library/sqlite3.html:

    .. code-block:: python

        import sqlite3
        conn = sqlite3.connect(':memory:')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE stocks
            (date text, trans text, symbol text, qty real, price real)
        ''')
        c.execute('''
            INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)
        ''')
        conn.commit()

        c.execute("SELECT * FROM stocks")
        print(repr(c.description))

    See also:

    - http://initd.org/psycopg/docs/cursor.html

    """

    @property
    @abstractmethod
    def description(self) \
            -> Optional[Sequence[Sequence[str,
                                          Optional[Type],  # not sure
                                          Optional[int], Optional[int],
                                          Optional[int], Optional[int],
                                          Optional[bool]]]]:
        """
        A sequence of column_description objects, where each column_description
        describes one result column and has the following items:

        - name
        - type_code
        - display_size
        - internal_size
        - precision
        - scale
        - null_ok

        The attribute is ``None`` for operations that don't return rows, and
        for un-executed cursors.

        """
        pass

    @property
    @abstractmethod
    def rowcount(self) -> int:
        pass

    @abstractmethod
    def callproc(self, procname: str, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def execute(self, operation: str, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def executemany(self, operation: str, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def fetchone(self, operation: str,
                 parameters: Sequence[Any]) -> Optional[Sequence[Any]]:
        pass

    @abstractmethod
    def fetchmany(self, size: int = None) -> Sequence[Sequence[Any]]:
        pass

    @abstractmethod
    def fetchall(self) -> Sequence[Sequence[Any]]:
        pass

    @abstractmethod
    def nextset(self) -> Optional[bool]:
        pass

    @property
    @abstractmethod
    def arraysize(self) -> int:
        # read/write attribute; see below
        pass

    @arraysize.setter
    @abstractmethod
    def arraysize(self, val: int) -> None:
        # https://stackoverflow.com/questions/35344209/python-abstract-property-setter-with-concrete-getter
        pass

    @abstractmethod
    def setinputsizes(self, sizes: Sequence[Union[Type, int]]) -> None:
        pass

    @abstractmethod
    def setoutputsize(self, size: int, column: Optional[int]) -> None:
        pass
