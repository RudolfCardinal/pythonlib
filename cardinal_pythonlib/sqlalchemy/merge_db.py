#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/merge_db.py

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

**Function "merge_db" to merge two databases via SQLAlchemy.**

*Notes:*

Note in passing: there is no common base class for SQLAlchemy ORM instances
(it's not :class:`DeclarativeMeta`). For example, in CamCOPS:

.. code-block:: none

    > Phq9.__bases__
    (<class 'camcops_server.cc_modules.cc_task.TaskHasPatientMixin'>,
     <class 'camcops_server.cc_modules.cc_task.Task'>,
     <class 'sqlalchemy.ext.declarative.api.Base'>)

... and that last :class:`Base` isn't a permanent class, just a newly named
thing; see :func:`sqlalchemy.ext.declarative.api.declarative_base`.

Again, with the CamCOPS classes:

.. code-block:: none

    > issubclass(Phq9, Base)
    True

    > issubclass(Base, DeclarativeMeta)
    False

    > Base.__bases__
    (<class 'object'>,)

So the best type hints we have are:

.. code-block:: none

    class: Type
    instance: object

"""

import logging
import sys
from typing import Any, Callable, Dict, List, Tuple, Type
import unittest

from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import lazyload, load_only
from sqlalchemy.orm import relationship
# noinspection PyProtectedMember
from sqlalchemy.orm.session import make_transient, Session, sessionmaker
from sqlalchemy.schema import sort_tables
from sqlalchemy.sql.schema import Column, ForeignKey, MetaData, Table
from sqlalchemy.sql.sqltypes import Integer, Text

from cardinal_pythonlib.dicts import map_keys_to_values
from cardinal_pythonlib.logs import BraceStyleAdapter, main_only_quicksetup_rootlogger  # noqa
from cardinal_pythonlib.sqlalchemy.dump import dump_database_as_insert_sql
from cardinal_pythonlib.sqlalchemy.orm_inspect import (
    rewrite_relationships,
    colname_to_attrname_dict,
    copy_sqla_object,
    get_orm_classes_by_table_name_from_base,
    get_pk_attrnames,
)
from cardinal_pythonlib.sqlalchemy.schema import (
    get_column_names,
    get_table_names,
)
from cardinal_pythonlib.sqlalchemy.session import (
    get_engine_from_session,
    get_safe_url_from_engine,
    get_safe_url_from_session,
    SQLITE_MEMORY_URL,
)
from cardinal_pythonlib.sqlalchemy.table_identity import TableIdentity

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# TableDependency; get_all_dependencies
# =============================================================================

class TableDependency(object):
    """
    Stores a table dependency for use in functions such as
    :func:`sqlalchemy.schema.sort_tables`, which requires a tuple of two
    :class:`Table` objects, in the order ``(parent, child)``, where ``child``
    depends on ``parent`` (e.g. a field like ``child.parent_id`` refers to
    ``parent.id``).
    """
    def __init__(self,
                 parent_table_id: TableIdentity = None,
                 child_table_id: TableIdentity = None,
                 parent_table: Table = None,
                 child_table: Table = None,
                 parent_tablename: str = None,
                 child_tablename: str = None,
                 metadata: MetaData = None) -> None:
        """
        The parent and child tables can be specified by name, :class:`Table`
        object, or our :class:`TableIdentity` descriptor class.
        """
        overspecified = "Don't specify table with both TableIdentity and " \
                        "Table/tablename"
        if parent_table_id:
            self._parent = parent_table_id
            assert parent_table is None and not parent_tablename, overspecified
        else:
            self._parent = TableIdentity(table=parent_table,
                                         tablename=parent_tablename,
                                         metadata=metadata)
        if child_table_id:
            self._child = child_table_id
            assert child_table is None and not child_tablename, overspecified
        else:
            self._child = TableIdentity(table=child_table,
                                        tablename=child_tablename,
                                        metadata=metadata)

    def __str__(self) -> str:
        return "{} -> {}".format(
            self.child_tablename, self.parent_tablename)

    def __repr__(self) -> str:
        return "TableDependency({!r} depends on {!r})".format(
            self.child_tablename, self.parent_tablename)

    def set_metadata(self, metadata: MetaData) -> None:
        """
        Sets the metadata for the parent and child tables.
        """
        self._parent.set_metadata(metadata)
        self._child.set_metadata(metadata)

    def set_metadata_if_none(self, metadata: MetaData) -> None:
        """
        Sets the metadata for the parent and child tables, unless they were
        set already.
        """
        self._parent.set_metadata_if_none(metadata)
        self._child.set_metadata_if_none(metadata)

    @property
    def parent_table(self) -> Table:
        """
        Returns the parent table as a :class:`Table`.
        """
        return self._parent.table

    @property
    def child_table(self) -> Table:
        """
        Returns the child table as a :class:`Table`.
        """
        return self._child.table

    @property
    def parent_tablename(self) -> str:
        """
        Returns the parent table's string name.
        """
        return self._parent.tablename

    @property
    def child_tablename(self) -> str:
        """
        Returns the child table's string name.
        """
        return self._child.tablename

    def sqla_tuple(self) -> Tuple[Table, Table]:
        """
        Returns the tuple ``(parent_table, child_table)``, both as
        :class:`Table` objects.
        """
        return self.parent_table, self.child_table


def get_all_dependencies(metadata: MetaData,
                         extra_dependencies: List[TableDependency] = None,
                         sort: bool = True) \
        -> List[TableDependency]:
    """
    Describes how the tables found in the metadata depend on each other.
    (If table B contains a foreign key to table A, for example, then B depends
    on A.)

    Args:
        metadata: the metadata to inspect
        extra_dependencies: additional table dependencies to specify manually
        sort: sort into alphabetical order of (parent, child) table names?

    Returns:
        a list of :class:`TableDependency` objects

    See :func:`sort_tables_and_constraints` for method.
    """
    extra_dependencies = extra_dependencies or []  # type: List[TableDependency]  # noqa
    for td in extra_dependencies:
        td.set_metadata_if_none(metadata)
    dependencies = set([td.sqla_tuple() for td in extra_dependencies])

    tables = list(metadata.tables.values())  # type: List[Table]

    for table in tables:
        for fkc in table.foreign_key_constraints:
            if fkc.use_alter is True:
                # http://docs.sqlalchemy.org/en/latest/core/constraints.html#sqlalchemy.schema.ForeignKeyConstraint.params.use_alter  # noqa
                continue

            dependent_on = fkc.referred_table
            if dependent_on is not table:
                dependencies.add((dependent_on, table))

        if hasattr(table, "_extra_dependencies"):
            # noinspection PyProtectedMember
            dependencies.update(
                (parent, table) for parent in table._extra_dependencies
            )

    dependencies = [
        TableDependency(parent_table=parent, child_table=child)
        for parent, child in dependencies
    ]
    if sort:
        dependencies.sort(key=lambda td_: (td_.parent_tablename,
                                           td_.child_tablename))
    return dependencies


# =============================================================================
# TableDependencyClassification; classify_tables_by_dependency_type
# =============================================================================

class TableDependencyClassification(object):
    """
    Class to describe/classify a table in terms of its dependencies.
    """
    def __init__(self,
                 table: Table,
                 children: List[Table] = None,
                 parents: List[Table] = None) -> None:
        """
        Args:
            table: the table in question
            children: its children (things that depend on it)
            parents: its parents (things that it depends on)
        """
        self.table = table
        self.children = children or []  # type: List[Table]
        self.parents = parents or []  # type: List[Table]
        self.circular = False
        self.circular_chain = []  # type: List[Table]

    @property
    def is_child(self) -> bool:
        """
        Is this table a child?
        """
        return bool(self.parents)

    @property
    def is_parent(self) -> bool:
        """
        Is this table a parent?
        """
        return bool(self.children)

    @property
    def standalone(self) -> bool:
        """
        Is this table standalone (neither a child nor a parent)?
        """
        return not self.is_child and not self.is_parent

    @property
    def tablename(self) -> str:
        """
        Returns the table's name.
        """
        return self.table.name

    @property
    def parent_names(self) -> List[str]:
        """
        Returns the names of this table's parents.
        """
        return [t.name for t in self.parents]

    @property
    def child_names(self) -> List[str]:
        """
        Returns the names of this table's children.
        """
        return [t.name for t in self.children]

    def set_circular(self, circular: bool, chain: List[Table] = None) -> None:
        """
        Mark this table as circular (or not).

        Args:
            circular: is it circular?
            chain: if it's circular, this should be the list of tables
                participating in the circular chain
        """
        self.circular = circular
        self.circular_chain = chain or []  # type: List[Table]

    @property
    def circular_description(self) -> str:
        """
        Description of the circular chain.
        """
        return " -> ".join(t.name for t in self.circular_chain)

    @property
    def description(self) -> str:
        """
        Short description.
        """
        if self.is_parent and self.is_child:
            desc = "parent+child"
        elif self.is_parent:
            desc = "parent"
        elif self.is_child:
            desc = "child"
        else:
            desc = "standalone"
        if self.circular:
            desc += "+CIRCULAR({})".format(self.circular_description)
        return desc

    def __str__(self) -> str:
        return "{}:{}".format(self.tablename, self.description)

    def __repr__(self) -> str:
        return "TableDependencyClassification({!r}:{})".format(
            self.tablename, self.description)


def classify_tables_by_dependency_type(
        metadata: MetaData,
        extra_dependencies: List[TableDependency] = None,
        sort: bool = True) \
        -> List[TableDependencyClassification]:
    """
    Inspects a metadata object (optionally adding other specified dependencies)
    and returns a list of objects describing their dependencies.

    Args:
        metadata: the :class:`MetaData` to inspect
        extra_dependencies: additional dependencies
        sort: sort the results by table name?

    Returns:
        list of :class:`TableDependencyClassification` objects, one for each
        table

    """
    tables = list(metadata.tables.values())  # type: List[Table]
    all_deps = get_all_dependencies(metadata, extra_dependencies)
    tdcmap = {}  # type: Dict[Table, TableDependencyClassification]
    for table in tables:
        parents = [td.parent_table for td in all_deps
                   if td.child_table == table]
        children = [td.child_table for td in all_deps
                    if td.parent_table == table]
        tdcmap[table] = TableDependencyClassification(
            table, parents=parents, children=children
        )

    # Check for circularity
    def parents_contain(start: Table,
                        probe: Table) -> Tuple[bool, List[Table]]:
        tdc_ = tdcmap[start]
        if probe in tdc_.parents:
            return True, [start, probe]
        for parent in tdc_.parents:
            contains_, chain_ = parents_contain(start=parent, probe=probe)
            if contains_:
                return True, [start] + chain_
        return False, []

    def children_contain(start: Table,
                         probe: Table) -> Tuple[bool, List[Table]]:
        tdc_ = tdcmap[start]
        if probe in tdc_.children:
            return True, [start, probe]
        for child in tdc_.children:
            contains_, chain_ = children_contain(start=child, probe=probe)
            if contains_:
                return True, [start] + chain_
        return False, []

    for table in tables:
        tdc = tdcmap[table]
        contains, chain = parents_contain(start=table, probe=table)
        if contains:
            tdc.set_circular(contains, chain)
        else:
            contains, chain = children_contain(start=table, probe=table)
            if contains:
                tdc.set_circular(contains, chain)
            else:
                tdc.set_circular(False)

    classifications = list(tdcmap.values())
    if sort:
        classifications.sort(key=lambda c: c.tablename)
    return classifications


# =============================================================================
# TranslationContext (for merge_db)
# =============================================================================

class TranslationContext(object):
    """
    Information-passing object for user callbacks from :func:`merge_db`.

    Args:

        oldobj:
            The old SQLAlchemy ORM object from the source session.

        newobj:
            The framework's go at building a new SQLAlchemy ORM object, which
            will be inserted into the destination session.

            The sequence is:

            1. ``newobj`` is created
            2. a :class:`TranslationContext` is created, referring to
               ``newobj``
            3. The ``translate_fn`` parameter to :func:`merge_db` will be
               called with the :class:`TranslationContext` as its parameter

               - the user-suppled :func:`translate_fn` function can, at this
                 point, modify the ``newobj`` attribute
               - if the user function sets the ``newobj`` attribute to
                 ``None``, this object will be skipped

            4. If the :class:`TranslationContext`'s ``newobj`` member is not
               ``None``, the new object is inserted into the destination
               session.

        objmap:
            A dictionary mapping old to new objects, for objects in tables
            other than standalone tables.

        table:
            SQLAlchemy ``Table`` object from the metadata. (Not necessarily
            bound to any session, but will reflect the structure of the
            destination, not necessarily the source, since the merge operation
            assumes that the metadata describes the destination.)

        tablename:
            Table name that corresponds to ``table``.

        src_session:
            The SQLAlchemy :class:`Session` object for the source.

        dst_session:
            The SQLAlchemy :class:`Session` object for the destination.

        src_engine:
            The SQLAlchemy :class:`Engine` object for the source.

        dst_engine:
            The SQLAlchemy :class:`Engine` object for the destination.

        missing_src_columns:
            Names of columns known to be present in the destination but absent
            from the source.

        info:
            Extra dictionary for additional user-specified information.

    It is possible that ``oldobj`` and ``newobj`` are the SAME OBJECT.

    """
    def __init__(self,
                 oldobj: object,
                 newobj: object,
                 objmap: Dict[object, object],
                 table: Table,
                 tablename: str,
                 src_session: Session,
                 dst_session: Session,
                 src_engine: Engine,
                 dst_engine: Engine,
                 src_table_names: List[str],
                 missing_src_columns: List[str] = None,
                 info: Dict[str, Any] = None) -> None:
        self.oldobj = oldobj
        self.newobj = newobj
        self.objmap = objmap
        self.table = table
        self.tablename = tablename
        self.src_session = src_session
        self.dst_session = dst_session
        self.src_engine = src_engine
        self.dst_engine = dst_engine
        self.src_table_names = src_table_names
        self.missing_src_columns = missing_src_columns or []  # type: List[str]
        self.info = info or {}  # type: Dict[str, Any]


# =============================================================================
# merge_db
# =============================================================================

def merge_db(base_class: Type,
             src_engine: Engine,
             dst_session: Session,
             allow_missing_src_tables: bool = True,
             allow_missing_src_columns: bool = True,
             translate_fn: Callable[[TranslationContext], None] = None,
             skip_tables: List[TableIdentity] = None,
             only_tables: List[TableIdentity] = None,
             tables_to_keep_pks_for: List[TableIdentity] = None,
             extra_table_dependencies: List[TableDependency] = None,
             dummy_run: bool = False,
             info_only: bool = False,
             report_every: int = 1000,
             flush_per_table: bool = True,
             flush_per_record: bool = False,
             commit_with_flush: bool = False,
             commit_at_end: bool = True,
             prevent_eager_load: bool = True,
             trcon_info: Dict[str, Any] = None) -> None:
    """
    Copies an entire database as far as it is described by ``metadata`` and
    ``base_class``, from SQLAlchemy ORM session ``src_session`` to
    ``dst_session``, and in the process:

    - creates new primary keys at the destination, or raises an error if it
      doesn't know how (typically something like: ``Field 'name' doesn't have a
      default value``)

    - maintains relationships, or raises an error if it doesn't know how

    This assumes that the tables exist.

    Args:
        base_class:
            your ORM base class, e.g. from ``Base = declarative_base()``

        src_engine:
            SQLALchemy :class:`Engine` for the source database

        dst_session:
            SQLAlchemy :class:`Session` for the destination database

        allow_missing_src_tables:
            proceed if tables are missing from the source (allowing you to
            import from older, incomplete databases)

        allow_missing_src_columns:
            proceed if columns are missing from the source (allowing you to
            import from older, incomplete databases)

        translate_fn:
            optional function called with each instance, so you can modify
            instances in the pipeline. Signature:

            .. code-block:: python

                def my_translate_fn(trcon: TranslationContext) -> None:
                    # We can modify trcon.newobj, or replace it (including
                    # setting trcon.newobj = None to omit this object).
                    pass

        skip_tables:
            tables to skip (specified as a list of :class:`TableIdentity`)

        only_tables:
            tables to restrict the processor to (specified as a list of
            :class:`TableIdentity`)

        tables_to_keep_pks_for:
            tables for which PKs are guaranteed to be safe to insert into the
            destination database, without modification (specified as a list of
            :class:`TableIdentity`)

        extra_table_dependencies:
            optional list of :class:`TableDependency` objects (q.v.)

        dummy_run:
            don't alter the destination database

        info_only:
            show info, then stop

        report_every:
            provide a progress report every *n* records

        flush_per_table:
            flush the session after every table (reasonable)

        flush_per_record:
            flush the session after every instance (AVOID this if tables may
            refer to themselves)

        commit_with_flush:
            ``COMMIT`` with each flush?

        commit_at_end:
            ``COMMIT`` when finished?

        prevent_eager_load:
            disable any eager loading (use lazy loading instead)

        trcon_info:
            additional dictionary passed to ``TranslationContext.info``
            (see :class:`.TranslationContext`)
    """

    log.info("merge_db(): starting")
    if dummy_run:
        log.warning("Dummy run only; destination will not be changed")

    # Check parameters before we modify them
    if only_tables is not None and not only_tables:
        log.warning("... only_tables == []; nothing to do")
        return

    # Finalize parameters
    skip_tables = skip_tables or []  # type: List[TableIdentity]
    only_tables = only_tables or []  # type: List[TableIdentity]
    tables_to_keep_pks_for = tables_to_keep_pks_for or []  # type: List[TableIdentity]  # noqa
    extra_table_dependencies = extra_table_dependencies or []  # type: List[TableDependency]  # noqa
    trcon_info = trcon_info or {}  # type: Dict[str, Any]

    # We need both Core and ORM for the source.
    # noinspection PyUnresolvedReferences
    metadata = base_class.metadata  # type: MetaData
    src_session = sessionmaker(bind=src_engine)()  # type: Session
    dst_engine = get_engine_from_session(dst_session)
    tablename_to_ormclass = get_orm_classes_by_table_name_from_base(base_class)

    # Tell all TableIdentity objects about their metadata
    for tilist in [skip_tables, only_tables, tables_to_keep_pks_for]:
        for ti in tilist:
            ti.set_metadata_if_none(metadata)
    for td in extra_table_dependencies:
        td.set_metadata_if_none(metadata)

    # Get all lists of tables as their names
    skip_table_names = [ti.tablename for ti in skip_tables]
    only_table_names = [ti.tablename for ti in only_tables]
    tables_to_keep_pks_for = [ti.tablename for ti in tables_to_keep_pks_for]
    # ... now all are of type List[str]

    # Safety check: this is an imperfect check for source == destination, but
    # it is fairly easy to pass in the wrong URL, so let's try our best:
    _src_url = get_safe_url_from_engine(src_engine)
    _dst_url = get_safe_url_from_session(dst_session)
    assert _src_url != _dst_url or _src_url == SQLITE_MEMORY_URL, (
        "Source and destination databases are the same!"
    )

    # Check the right tables are present.
    src_tables = sorted(get_table_names(src_engine))
    dst_tables = sorted(list(tablename_to_ormclass.keys()))
    log.debug("Source tables: {!r}", src_tables)
    log.debug("Destination tables: {!r}", dst_tables)
    if not allow_missing_src_tables:
        missing_tables = sorted(
            d for d in dst_tables
            if d not in src_tables and d not in skip_table_names
        )
        if missing_tables:
            raise RuntimeError("The following tables are missing from the "
                               "source database: " + repr(missing_tables))

    table_num = 0
    overall_record_num = 0

    tables = list(metadata.tables.values())  # type: List[Table]
    # Very helpfully, MetaData.sorted_tables produces tables in order of
    # relationship dependency ("each table is preceded by all tables which
    # it references");
    # http://docs.sqlalchemy.org/en/latest/core/metadata.html
    # HOWEVER, it only works if you specify ForeignKey relationships
    # explicitly.
    # We can also add in user-specified dependencies, and therefore can do the
    # sorting in one step with sqlalchemy.schema.sort_tables:
    ordered_tables = sort_tables(
        tables,
        extra_dependencies=[td.sqla_tuple() for td in extra_table_dependencies]
    )
    # Note that the ordering is NOT NECESSARILY CONSISTENT, though (in that
    # the order of stuff it doesn't care about varies across runs).
    all_dependencies = get_all_dependencies(metadata, extra_table_dependencies)
    dep_classifications = classify_tables_by_dependency_type(
        metadata, extra_table_dependencies)
    circular = [tdc for tdc in dep_classifications if tdc.circular]
    assert not circular, "Circular dependencies! {!r}".format(circular)
    log.debug("All table dependencies: {}",
              "; ".join(str(td) for td in all_dependencies))
    log.debug("Table dependency classifications: {}",
              "; ".join(str(c) for c in dep_classifications))
    log.info("Processing tables in the order: {!r}",
             [table.name for table in ordered_tables])

    objmap = {}

    def flush() -> None:
        if not dummy_run:
            log.debug("Flushing session")
            dst_session.flush()
            if commit_with_flush:
                log.debug("Committing...")
                dst_session.commit()

    def translate(oldobj_: object, newobj_: object) -> object:
        if translate_fn is None:
            return newobj_
        tc = TranslationContext(oldobj=oldobj_,
                                newobj=newobj_,
                                objmap=objmap,
                                table=table,
                                tablename=tablename,
                                src_session=src_session,
                                dst_session=dst_session,
                                src_engine=src_engine,
                                dst_engine=dst_engine,
                                missing_src_columns=missing_columns,
                                src_table_names=src_tables,
                                info=trcon_info)
        translate_fn(tc)
        if tc.newobj is None:
            log.debug("Instance skipped by user-supplied translate_fn")
        return tc.newobj

    # -------------------------------------------------------------------------
    # Now, per table/ORM class...
    # -------------------------------------------------------------------------
    for table in ordered_tables:
        tablename = table.name

        if tablename in skip_table_names:
            log.info("... skipping table {!r} (as per skip_tables)", tablename)
            continue
        if only_table_names and tablename not in only_table_names:
            log.info("... ignoring table {!r} (as per only_tables)", tablename)
            continue
        if allow_missing_src_tables and tablename not in src_tables:
            log.info("... ignoring table {!r} (not in source database)",
                     tablename)
            continue
        table_num += 1
        table_record_num = 0

        src_columns = sorted(get_column_names(src_engine, tablename))
        dst_columns = sorted([column.name for column in table.columns])
        missing_columns = sorted(list(set(dst_columns) - set(src_columns)))

        if not allow_missing_src_columns:
            if missing_columns:
                raise RuntimeError(
                    "The following columns are missing from source table "
                    "{!r}: {!r}".format(tablename, missing_columns))

        orm_class = tablename_to_ormclass[tablename]
        pk_attrs = get_pk_attrnames(orm_class)
        c2a = colname_to_attrname_dict(orm_class)
        missing_attrs = map_keys_to_values(missing_columns, c2a)
        tdc = [tdc for tdc in dep_classifications if tdc.table == table][0]

        log.info("Processing table {!r} via ORM class {!r}",
                 tablename, orm_class)
        log.debug("PK attributes: {!r}", pk_attrs)
        log.debug("Table: {!r}", table)
        log.debug("Dependencies: parents = {!r}; children = {!r}",
                  tdc.parent_names, tdc.child_names)

        if info_only:
            log.debug("info_only; skipping table contents")
            continue

        def wipe_primary_key(inst: object) -> None:
            for attrname in pk_attrs:
                setattr(inst, attrname, None)

        query = src_session.query(orm_class)

        if allow_missing_src_columns and missing_columns:
            src_attrs = map_keys_to_values(src_columns, c2a)
            log.info("Table {} is missing columns {} in the source",
                     tablename, missing_columns)
            log.debug("... using only columns {} via attributes {}",
                      src_columns, src_attrs)
            query = query.options(load_only(*src_attrs))
            # PROBLEM: it will not ignore the PK.

        if prevent_eager_load:
            query = query.options(lazyload("*"))

        wipe_pk = tablename not in tables_to_keep_pks_for

        # How best to deal with relationships?
        #
        # This doesn't work:
        # - process tables in order of dependencies, eager-loading
        #   relationships with
        #       for relationship in insp.mapper.relationships:  # type: RelationshipProperty  # noqa
        #           related_col = getattr(orm_class, relationship.key)
        #           query = query.options(joinedload(related_col))
        # - expunge from old session / make_transient / wipe_primary_key/ add
        #   to new session
        # ... get errors like
        #       sqlalchemy.exc.InvalidRequestError: Object '<Parent at
        #       0x7f99492440b8>' is already attached to session '7' (this is
        #       '6')
        #
        # ... at the point of dst_session.add(instance)
        # ... when adding the object on the child side of the relationship
        # ... I suspect that we move the Parent from session S to session D,
        #     but when we eager-load the Parent from the Child, that makes
        #     another in session S, so when we add the Child to session D, its
        #     parent is in session S, which is wrong.
        #
        # We must, therefore, take a more interventional approach, in which we
        # maintain a copy of the old object, make a copy using
        # copy_sqla_object, and re-assign relationships accordingly.

        for instance in query.all():
            # log.debug("Source instance: {!r}", instance)
            table_record_num += 1
            overall_record_num += 1
            if table_record_num % report_every == 0:
                log.info("... progress{}: on table {} ({}); record {} this "
                         "table; overall record {}",
                         " (DUMMY RUN)" if dummy_run else "",
                         table_num, tablename,
                         table_record_num, overall_record_num)

            if tdc.standalone:
                # Our table has neither parents nor children. We can therefore
                # simply move the instance from one session to the other,
                # blanking primary keys.

                # https://stackoverflow.com/questions/14636192/sqlalchemy-modification-of-detached-object  # noqa
                src_session.expunge(instance)
                make_transient(instance)
                if wipe_pk:
                    wipe_primary_key(instance)

                instance = translate(instance, instance)
                if not instance:
                    continue  # translate_fn elected to skip it

                if not dummy_run:
                    dst_session.add(instance)
                    # new PK will be created when session is flushed

            else:
                # Our table has either parents or children. We therefore make
                # a copy and place the COPY in the destination session. If
                # this object may be a parent, we maintain a log (in objmap)
                # of the old-to-new mapping. If this object is a child, we
                # re-assign its relationships based on the old-to-new mapping
                # (since we will have processed the parent table first, having
                # carefully ordered them in advance).

                oldobj = instance  # rename for clarity
                newobj = copy_sqla_object(
                    oldobj, omit_pk=wipe_pk, omit_fk=True,
                    omit_attrs=missing_attrs, debug=False
                )

                rewrite_relationships(oldobj, newobj, objmap, debug=False,
                                      skip_table_names=skip_table_names)

                newobj = translate(oldobj, newobj)
                if not newobj:
                    continue  # translate_fn elected to skip it

                if not dummy_run:
                    dst_session.add(newobj)
                    # new PK will be created when session is flushed

                if tdc.is_parent:
                    objmap[oldobj] = newobj  # for its children's benefit

            if flush_per_record:
                flush()

        if flush_per_table:
            flush()

    flush()
    if commit_at_end:
        log.debug("Committing...")
        dst_session.commit()
    log.info("merge_db(): finished")


# =============================================================================
# Unit tests
# =============================================================================

class MergeTestMixin(object):
    """
    Mixin to create source/destination databases as in-memory SQLite databases
    for unit testing purposes.
    """
    def __init__(self, *args, echo: bool = False, **kwargs) -> None:
        self.src_engine = create_engine(SQLITE_MEMORY_URL, echo=echo)  # type: Engine  # noqa
        self.dst_engine = create_engine(SQLITE_MEMORY_URL, echo=echo)  # type: Engine  # noqa
        self.src_session = sessionmaker(bind=self.src_engine)()  # type: Session  # noqa
        self.dst_session = sessionmaker(bind=self.dst_engine)()  # type: Session  # noqa
        # log.critical("SRC SESSION: {}".format(self.src_session))
        # log.critical("DST SESSION: {}".format(self.dst_session))

        self.Base = declarative_base()

        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)

    def dump_source(self) -> None:
        log.warning("Dumping source")
        dump_database_as_insert_sql(
            engine=self.src_engine,
            fileobj=sys.stdout,
            include_ddl=True,
            multirow=True
        )

    def dump_destination(self) -> None:
        log.warning("Dumping destination")
        dump_database_as_insert_sql(
            engine=self.dst_engine,
            fileobj=sys.stdout,
            include_ddl=True,
            multirow=True
        )

    def do_merge(self, dummy_run: bool = False) -> None:
        merge_db(
            base_class=self.Base,
            src_engine=self.src_engine,
            dst_session=self.dst_session,
            allow_missing_src_tables=False,
            allow_missing_src_columns=True,
            translate_fn=None,
            skip_tables=None,
            only_tables=None,
            extra_table_dependencies=None,
            dummy_run=dummy_run,
            report_every=1000
        )


class MergeTestPlain(MergeTestMixin, unittest.TestCase):
    """
    Unit tests for a simple merge operation.
    
    *Notes re unit testing:*

    - tests are found by virtue of the fact that their names start with
      "test"; see
      https://docs.python.org/3.6/library/unittest.html#basic-example

    - A separate instance of the class is created for each test, and in each
      case is called with:
      
      .. code-block:: python

        setUp()
        testSOMETHING()
        tearDown()

      ... see https://docs.python.org/3.6/library/unittest.html#test-cases

    - If you use mixins, they go AFTER :class:`unittest.TestCase`; see
      https://stackoverflow.com/questions/1323455/python-unit-test-with-base-and-sub-class

    """  # noqa
    def setUp(self) -> None:
        # log.info('In setUp()')

        class Parent(self.Base):
            __tablename__ = "parent"
            id = Column(Integer, primary_key=True, autoincrement=True)
            name = Column(Text)

        class Child(self.Base):
            __tablename__ = "child"
            id = Column(Integer, primary_key=True, autoincrement=True)
            name = Column(Text)
            parent_id = Column(Integer, ForeignKey("parent.id"))
            parent = relationship(Parent)

        self.Base.metadata.create_all(self.src_engine)
        self.Base.metadata.create_all(self.dst_engine)

        p1 = Parent(name="Parent 1")
        p2 = Parent(name="Parent 2")
        c1 = Child(name="Child 1")
        c2 = Child(name="Child 2")
        c1.parent = p1
        c2.parent = p2
        self.src_session.add_all([p1, p2, c1, c2])
        self.src_session.commit()

    def tearDown(self) -> None:
        pass
        # log.info('In tearDown()')

    def test_source(self) -> None:
        self.dump_source()

    def test_dummy(self) -> None:
        log.info("Testing merge_db() in dummy run mode")
        self.do_merge(dummy_run=True)
        self.dst_session.commit()
        self.dump_destination()

    def test_merge_to_empty(self) -> None:
        log.info("Testing merge_db() to empty database")
        self.do_merge(dummy_run=False)
        self.dst_session.commit()
        self.dump_destination()

    # @unittest.skip
    def test_merge_to_existing(self) -> None:
        log.info("Testing merge_db() to pre-populated database")
        self.do_merge(dummy_run=False)
        self.dst_session.commit()
        self.do_merge(dummy_run=False)
        self.dst_session.commit()
        self.dump_destination()


class MergeTestCircular(MergeTestMixin, unittest.TestCase):
    """
    Unit tests including a circular dependency, which will fail.
    """

    @unittest.expectedFailure
    def test_setup_circular(self):

        class Parent(self.Base):
            __tablename__ = "parent"
            id = Column(Integer, primary_key=True, autoincrement=True)
            name = Column(Text)
            child_id = Column(Integer, ForeignKey("child.id"))
            child = relationship("Child", foreign_keys=[child_id])

        class Child(self.Base):
            __tablename__ = "child"
            id = Column(Integer, primary_key=True, autoincrement=True)
            name = Column(Text)
            parent_id = Column(Integer, ForeignKey("parent.id"))
            parent = relationship(Parent, foreign_keys=[parent_id])

        self.Base.metadata.create_all(self.src_engine)
        self.Base.metadata.create_all(self.dst_engine)

        p1 = Parent(name="Parent 1")
        p2 = Parent(name="Parent 2")
        c1 = Child(name="Child 1")
        c2 = Child(name="Child 2")
        c1.parent = p1
        c2.parent = p2
        p1.child = c1
        p2.child = c2
        self.src_session.add_all([p1, p2, c1, c2])
        self.src_session.commit()  # will raise sqlalchemy.exc.CircularDependencyError  # noqa

    @unittest.expectedFailure
    def test_circular(self) -> None:
        self.test_setup_circular()  # fails here
        log.info("Testing merge_db() with circular relationship")
        self.do_merge(dummy_run=False)  # would fail here, but fails earlier!
        self.dst_session.commit()
        self.dump_destination()


# =============================================================================
# main
# =============================================================================
# run with "python merge_db.py -v" to be verbose

if __name__ == "__main__":
    main_only_quicksetup_rootlogger()
    unittest.main()
