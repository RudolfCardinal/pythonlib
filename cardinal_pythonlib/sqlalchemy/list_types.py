#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/list_types.py

"""
===============================================================================

    Original code copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).

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
from typing import List, Optional

from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.sqltypes import Text, UnicodeText
from sqlalchemy.sql.type_api import TypeDecorator

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# StringListType
# =============================================================================

class StringListType(TypeDecorator):
    r"""
    Store a list of strings as CSV.
    (Rather less arbitrary in its encoding requirements than e.g.
    http://sqlalchemy-utils.readthedocs.io/en/latest/_modules/sqlalchemy_utils/types/scalar_list.html#ScalarListType.)
    
    - 2019-01-01: removed trailing ``\r\n`` (via ``lineterminator=""``).
    
      Some related test code:
    
      .. code-block:: python

        import csv
        from io import StringIO
        
        pythonlist = [None, 1, "string", "commas, within string", "line 1\nline2"]
        
        output_1 = StringIO()
        wr_1 = csv.writer(output_1, quoting=csv.QUOTE_ALL)  # appends '\r\n'
        wr_1.writerow(pythonlist)
        csvstring_1 = output_1.getvalue()
        print(repr(csvstring_1))
        backtopython_1 = list(csv.reader([csvstring_1]))[0]
        print(repr(backtopython_1))
        
        output_2 = StringIO()
        wr_2 = csv.writer(output_2, quoting=csv.QUOTE_ALL, lineterminator="")
        wr_2.writerow(pythonlist)
        csvstring_2 = output_2.getvalue()
        print(repr(csvstring_2))
        backtopython_2 = list(csv.reader([csvstring_2]))[0]
        print(repr(backtopython_2))
        
        assert len(csvstring_1) > len(csvstring_2)
        assert backtopython_1 == backtopython_2

      So:
    
      - The newline terminator is obviously unnecessary for something that will
        always be a single CSV line.
      - Eliminating it saves two bytes and adds clarity in the database
        representation.
      - Eliminating it keeps the system back-compatible, since the reader
        happily reads things without the line terminator.
        
    - **NOTE** in particular that this does not behave completely like a plain
      Python list on the Python side, as follows.
      
    - When an ORM object is created, the default value on the Python side is
      ``None``.
      
      - The SQLAlchemy ``default`` option is invoked at ``INSERT``, not at ORM
        object creation; see
        https://docs.sqlalchemy.org/en/latest/core/metadata.html#sqlalchemy.schema.Column.params.default.
        
      - The SQLAlchemy ``server_default`` is the DDL ``DEFAULT`` value, not a
        Python default.
        
      - On database load, everything is fine (as ``process_result_value`` will
        be called, which can translate a database ``NULL`` to a Python ``[]``).
        
      - So that means that **if you want the field to be a list rather than
        None from the outset,** you must set it to ``[]`` from ``__init__()``.
        
    - Secondly, SQLAlchemy makes its columns behave in a special way **upon
      assignment**. So, in particular, ``mylist.append(value)`` will not itself
      mark the field as "dirty" and in need of writing to the database.
      
      - Internally, support we define (on the class) ``mycol =
        Column(Integer)``, and then create an instance via ``instance =
        cls()``.
        
      - Then ``cls.mycol`` will actually be of type
        :class:`sqlalchemy.orm.attributes.InstrumentedAttribute`, and
        ``instance.mycol`` will be of type ``int`` (or ``NoneType`` if it's
        ``None``).
        
        .. code-block:: python
        
            from sqlalchemy.ext.declarative import declarative_base
            from sqlalchemy.sql.schema import Column
            from sqlalchemy.sql.sqltypes import Integer
            
            Base = declarative_base()
            
            class MyClass(Base):
                __tablename__ = "mytable"
                pk = Column(Integer, primary_key=True)
                mycol = Column(Integer)
                
            instance = MyClass()
            type(MyClass.pk)  # <class 'sqlalchemy.orm.attributes.InstrumentedAttribute'>
            type(instance.pk)  # <class 'NoneType'>

      - The class :class:`sqlalchemy.orm.attributes.InstrumentedAttribute`
        implements :meth:`__set__`, :meth:`__delete__`, and :meth:`__get__`.
        This means that when you write ``instance.mycol = 5``, it calls the
        ``__set__()`` function; see
        https://docs.python.org/3.7/howto/descriptor.html.
      
      - So, for a list (e.g. ``mylist = Column(StringListType)``, if you write
        ``mylist = [value1, value2]``, it will call the appropriate
        ``__set__()`` function and mark the field as "dirty" (see e.g.
        :meth:`sqlalchemy.orm.attributes.ScalarAttributeImpl.set`). **But** if
        ``mylist`` is already a list and you write ``mylist.append(value)``,
        the ``__set__()`` function won't be called.
      
      - If you haven't yet written the instance to the database, this doesn't
        matter; "new" values are considered dirty and are written to the
        database fine. But if you (a) create, (b) save, and then (c) append to
        a list, the change won't be noticed. Since SQLAlchemy can save objects
        for you as soon as another object needs to know it's PK, the fact that
        (b) has happened may not be obvious.
      
      - Therefore, in short, **beware append() and use assignment** for these
        sorts of lists, if this might apply; e.g. ``mylist = mylist +
        [value]``.
        
      - Don't use ``+=``, either; that calls ``list.__iadd__()`` and modifies
        the existing list, rather than calling
        ``InstrumentedAttribute.__set__()``.
        
    - So one method is to ignore ``__init__()`` (meaning new instances will
      have the list-type field set to ``None``) and then using this sort of
      access function:
      
      .. code-block:: python
        
        def add_to_mylist(self, text: str) -> None:
            if self.mylist is None:
                self.mylist = [text]
            else:
                # noinspection PyAugmentAssignment
                self.mylist = self.mylist + [text]  # not "append()", not "+="
    
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
        wr = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="")
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

    # Could also use "process_literal_param = process_bind_param"
    # or vice versa, but this adds some clarity via docstrings.

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

    **Note:** see :class:`StringListType` for a general discussion about
    SQLAlchemy types where the Python representation is a list; they can seem
    slightly unusual.
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
