#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/table_identity.py

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

**Class to refer to database tables either by name or by SQLAlchemy Table
object.**

"""

import logging

from sqlalchemy.sql.schema import MetaData, Table

from cardinal_pythonlib.logs import BraceStyleAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# TableIdentity
# =============================================================================

class TableIdentity(object):
    """
    Convenient way of passing around SQLAlchemy :class:`Table` objects when you
    might know either either its name or the :class:`Table` object itself.
    """
    def __init__(self,
                 tablename: str = None,
                 table: Table = None,
                 metadata: MetaData = None) -> None:
        """
        Initialize with either ``tablename`` or ``table``, not both.

        Args:
            tablename: string name of the table
            table: SQLAlchemy :class:`Table` object
            metadata: optional :class:`MetaData` object
        """
        assert table is not None or tablename, "No table information provided"
        assert not (tablename and table is not None), (
            "Specify either table or tablename, not both")
        self._table = table
        self._tablename = tablename
        self._metadata = metadata

    def __str__(self) -> str:
        return self.tablename

    def __repr__(self) -> str:
        return (
            "TableIdentity(table={!r}, tablename={!r}, metadata={!r}".format(
                self._table, self._tablename, self._metadata
            )
        )

    @property
    def table(self) -> Table:
        """
        Returns a SQLAlchemy :class:`Table` object. This is either the
        :class:`Table` object that was used for initialization, or one that
        was constructed from the ``tablename`` plus the ``metadata``.
        """
        if self._table is not None:
            return self._table
        assert self._metadata, (
            "Must specify metadata (in constructor or via set_metadata()/"
            "set_metadata_if_none() before you can get a Table from a "
            "tablename"
        )
        for table in self._metadata.tables.values():  # type: Table
            if table.name == self._tablename:
                return table
        raise ValueError("No table named {!r} is present in the "
                         "metadata".format(self._tablename))

    @property
    def tablename(self) -> str:
        """
        Returns the string name of the table.
        """
        if self._tablename:
            return self._tablename
        return self.table.name

    def set_metadata(self, metadata: MetaData) -> None:
        """
        Sets the :class:`MetaData`.
        """
        self._metadata = metadata

    def set_metadata_if_none(self, metadata: MetaData) -> None:
        """
        Sets the :class:`MetaData` unless it was set already.
        """
        if self._metadata is None:
            self._metadata = metadata
