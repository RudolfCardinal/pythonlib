#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/list_types.py

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

**SQLAlchemy type classes to store different kinds of lists in a database.**

"""

import csv
from io import StringIO
import logging
from typing import List, Optional

from cardinal_pythonlib.logs import BraceStyleAdapter
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.sqltypes import Text, UnicodeText
from sqlalchemy.sql.type_api import TypeDecorator

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# StringListType
# =============================================================================

class StringListType(TypeDecorator):
    """
    Store a list of strings as CSV.
    (Rather less arbitrary in its encoding requirements than e.g.
    http://sqlalchemy-utils.readthedocs.io/en/latest/_modules/sqlalchemy_utils/types/scalar_list.html#ScalarListType.)
    """  # noqa
    impl = UnicodeText()

    @property
    def python_type(self):
        return list

    @staticmethod
    def _strlist_to_dbstr(strlist: Optional[List[str]]) -> str:
        if not strlist:
            return ""
        output = StringIO()
        wr = csv.writer(output, quoting=csv.QUOTE_ALL)
        wr.writerow(strlist)
        return output.getvalue()

    @staticmethod
    def _dbstr_to_strlist(dbstr: Optional[str]) -> List[str]:
        if not dbstr:
            return []
        try:
            return list(csv.reader([dbstr]))[0]
            # ... list( generator( list_of_lines ) )[first_line]
        except csv.Error:
            log.warning("StringListType: Unable to convert database value of "
                        "{!r} to Python; returning empty list", dbstr)
            return []

    def process_bind_param(self, value: Optional[List[str]],
                           dialect: Dialect) -> str:
        """Convert things on the way from Python to the database."""
        retval = self._strlist_to_dbstr(value)
        return retval

    def process_literal_param(self, value: Optional[List[str]],
                              dialect: Dialect) -> str:
        """Convert things on the way from Python to the database."""
        retval = self._strlist_to_dbstr(value)
        return retval

    def process_result_value(self, value: Optional[str],
                             dialect: Dialect) -> List[str]:
        """Convert things on the way from the database to Python."""
        retval = self._dbstr_to_strlist(value)
        return retval


# =============================================================================
# IntListType
# =============================================================================

class IntListType(TypeDecorator):
    """
    Store a list of integers as CSV.
    """
    impl = Text()

    @property
    def python_type(self):
        return list

    @staticmethod
    def _intlist_to_dbstr(intlist: Optional[List[int]]) -> str:
        if not intlist:
            return ""
        return ",".join(str(x) for x in intlist)

    @staticmethod
    def _dbstr_to_intlist(dbstr: Optional[str]) -> List[int]:
        if not dbstr:
            return []
        try:
            return [int(x) for x in dbstr.split(",")]
        except (TypeError, ValueError):
            log.warning("IntListType: Unable to convert database value of {!r}"
                        " to Python; returning empty list", dbstr)
            return []

    def process_bind_param(self, value: Optional[List[int]],
                           dialect: Dialect) -> str:
        """Convert things on the way from Python to the database."""
        retval = self._intlist_to_dbstr(value)
        return retval

    def process_literal_param(self, value: Optional[List[int]],
                              dialect: Dialect) -> str:
        """Convert things on the way from Python to the database."""
        retval = self._intlist_to_dbstr(value)
        return retval

    def process_result_value(self, value: Optional[str],
                             dialect: Dialect) -> List[int]:
        """Convert things on the way from the database to Python."""
        retval = self._dbstr_to_intlist(value)
        return retval
