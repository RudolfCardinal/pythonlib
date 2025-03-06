#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/merge_db.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

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

from functools import total_ordering
import logging
from typing import Any, Callable, Dict, List, Set, Tuple, Type

from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import lazyload, load_only
from sqlalchemy.orm.session import make_transient, Session, sessionmaker
from sqlalchemy.schema import sort_tables
from sqlalchemy.sql.schema import MetaData, Table

from cardinal_pythonlib.dicts import map_keys_to_values
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


# =============================================================================
# TableDependency; get_all_dependencies
# =============================================================================


@total_ordering
class TableDependency(object):
    """
    Stores a table dependency for use in functions such as
    :func:`sqlalchemy.schema.sort_tables`, which requires a tuple of two
    :class:`Table` objects, in the order ``(parent, child)``, where ``child``
    depends on ``parent`` (e.g. a field like ``child.parent_id`` refers to
    ``parent.id``).
    """

    def __init__(
        self,
        parent_table_id: TableIdentity = None,
        child_table_id: TableIdentity = None,
        parent_table: Table = None,
        child_table: Table = None,
        parent_tablename: str = None,
        child_tablename: str = None,
        metadata: MetaData = None,
    ) -> None:
        """
        The parent and child tables can be specified by name, :class:`Table`
        object, or our :class:`TableIdentity` descriptor class.
        """
        overspecified = (
            "Don't specify table with both TableIdentity and "
            "Table/tablename"
        )
        if parent_table_id:
            self._parent = parent_table_id
            assert parent_table is None and not parent_tablename, overspecified
        else:
            self._parent = TableIdentity(
                table=parent_table,
                tablename=parent_tablename,
                metadata=metadata,
            )
        if child_table_id:
            self._child = child_table_id
            assert child_table is None and not child_tablename, overspecified
        else:
            self._child = TableIdentity(
                table=child_table, tablename=child_tablename, metadata=metadata
            )

    def __str__(self) -> str:
        return f"{self.child_tablename} -> {self.parent_tablename}"

    def __repr__(self) -> str:
        return (
            f"TableDependency({self.child_tablename!r} "
            f"depends on {self.parent_tablename!r})"
        )

    def __lt__(self, other: "TableDependency") -> bool:
        """
        Define a sort order.
        """
        return (self.child_tablename, self.parent_tablename) < (
            other.child_tablename,
            other.parent_tablename,
        )

    def __eq__(self, other: "TableDependency") -> bool:
        return (
            self.child_tablename == other.child_tablename
            and self.parent_tablename == other.parent_tablename
        )

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


def _get_dependencies_for_table(
    table: Table, even_use_alter: bool = False
) -> Set[Tuple[Table, Table]]:
    """
    Returns dependencies for a single table.

    Args:
        table:
            A SQLAlchemy Table object.
        even_use_alter:
            Even include relationships with ``use_alter`` set. See
            https://docs.sqlalchemy.org/en/latest/core/constraints.html#sqlalchemy.schema.ForeignKeyConstraint.params.use_alter

    Returns:
        A set of tuples of Tables: (parent_that_this_table_dependent_on,
        this_table_child).

    See :func:`sqlalchemy.sql.ddl.sort_tables_and_constraints` for method.
    """
    dependencies: Set[Tuple[Table, Table]] = set()
    # Add via (a) foreign_key_constraints, and (b) _extra_dependencies. This is
    # an SQLAlchemy internal; see its sort_tables_and_constraints function as
    # above.
    # log.debug(
    #     f"_get_dependencies_for_table: {table.name=}; "
    #     f"{len(table.foreign_key_constraints)=}"
    # )
    for fkc in table.foreign_key_constraints:
        # log.debug(f"- {fkc.use_alter=}; {fkc.referred_table.name=}")
        if fkc.use_alter is True and not even_use_alter:
            continue
        dependent_on = fkc.referred_table
        if dependent_on is not table:
            dependencies.add((dependent_on, table))
    if hasattr(table, "_extra_dependencies"):
        # noinspection PyProtectedMember
        dependencies.update(
            (parent, table) for parent in table._extra_dependencies
        )
    return dependencies


def get_all_dependencies(
    metadata: MetaData,
    extra_dependencies: List[TableDependency] = None,
    skip_dependencies: List[TableDependency] = None,
    sort: bool = False,
    even_use_alter: bool = False,
    debug: bool = False,
) -> List[TableDependency]:
    """
    Describes how the tables found in the metadata depend on each other.
    (If table B contains a foreign key to table A, for example, then B depends
    on A.)

    Args:
        metadata:
            The metadata to inspect.
        extra_dependencies:
            Additional table dependencies to specify manually.
        skip_dependencies:
            Additional table dependencies to IGNORE.
        sort:
            Sort into alphabetical order of (parent, child) table names?
        even_use_alter:
            Even include relationships with ``use_alter`` set. See SQLAlchemy
            documentation.
        debug:
            Show debugging information.

    Returns:
        a list of :class:`TableDependency` objects
    """
    # First deal with user-specified dependencies.
    extra_dependencies: List[TableDependency] = extra_dependencies or []
    for td in extra_dependencies:
        td.set_metadata_if_none(metadata)
    dependencies: Set[Tuple[Table, Table]] = set(
        [td.sqla_tuple() for td in extra_dependencies]
    )
    if debug:
        readable = [str(td) for td in extra_dependencies]
        log.debug(f"get_all_dependencies: user specified: {readable!r}")

    # Add dependencies from tables.
    tables: List[Table] = list(metadata.tables.values())
    for table in tables:
        tdep = _get_dependencies_for_table(
            table, even_use_alter=even_use_alter
        )
        if debug:
            parents = [tt[0].name for tt in tdep]
            log.debug(
                f"get_all_dependencies: for table {table.name!r}, "
                f"adding dependencies: {parents}"
            )
        dependencies.update(tdep)

    # Remove explicitly specified dependencies to skip.
    skip_dependencies: List[TableDependency] = skip_dependencies or []
    for sd in skip_dependencies:
        dependencies.remove(sd.sqla_tuple())

    # Convert from set to list
    dependencies: List[TableDependency] = [
        TableDependency(parent_table=parent, child_table=child)
        for parent, child in dependencies
    ]
    if sort:
        dependencies.sort(
            key=lambda td_: (td_.parent_tablename, td_.child_tablename)
        )
    return dependencies


# =============================================================================
# TableDependencyClassification; classify_tables_by_dependency_type
# =============================================================================


class TableDependencyClassification(object):
    """
    Class to describe/classify a table in terms of its dependencies.
    """

    def __init__(
        self,
        table: Table,
        children: List[Table] = None,
        parents: List[Table] = None,
    ) -> None:
        """
        Args:
            table: the table in question
            children: its children (things that depend on it)
            parents: its parents (things that it depends on)
        """
        self.table: Table = table
        self.children: List[Table] = children or []
        self.parents: List[Table] = parents or []
        self.circular: bool = False
        self.circular_chain: List[Table] = []

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
        self.circular_chain = chain or []

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
            desc += f"+CIRCULAR({self.circular_description})"
        return desc

    def __str__(self) -> str:
        ptxt = ", ".join(sorted(p.name for p in self.parents))
        circ = (
            f"; CIRCULAR({self.circular_description})" if self.circular else ""
        )
        return f"{self.tablename}(depends on [{ptxt}]{circ})"

    def __repr__(self) -> str:
        return (
            f"TableDependencyClassification("
            f"{self.tablename!r}:{self.description})"
        )


def classify_tables_by_dependency_type(
    metadata: MetaData,
    extra_dependencies: List[TableDependency] = None,
    skip_dependencies: List[TableDependency] = None,
    all_dependencies: List[TableDependency] = None,
    even_use_alter: bool = False,
    sort: bool = True,
) -> List[TableDependencyClassification]:
    """
    Inspects a metadata object (optionally adding other specified dependencies)
    and returns a list of objects describing their dependencies.

    Args:
        metadata:
            the :class:`MetaData` to inspect
        extra_dependencies:
            Additional dependencies. (Not used if you specify
            all_dependencies.)
        skip_dependencies:
            Additional table dependencies to IGNORE. (Not used if you specify
            all_dependencies.)
        all_dependencies:
            If you have precalculated all dependencies, you can pass that in
            here, to save redoing the work.
        even_use_alter:
            Even include relationships with ``use_alter`` set. See SQLAlchemy
            documentation. (Not used if you specify all_dependencies.)
        sort:
            sort the results by table name?

    Returns:
        list of :class:`TableDependencyClassification` objects, one for each
        table

    """
    tables: List[Table] = list(metadata.tables.values())
    all_deps = all_dependencies or get_all_dependencies(
        metadata=metadata,
        extra_dependencies=extra_dependencies,
        skip_dependencies=skip_dependencies,
        even_use_alter=even_use_alter,
    )
    tdcmap: Dict[Table, TableDependencyClassification] = {}
    for table in tables:
        parents = [
            td.parent_table for td in all_deps if td.child_table == table
        ]
        children = [
            td.child_table for td in all_deps if td.parent_table == table
        ]
        tdcmap[table] = TableDependencyClassification(
            table, parents=parents, children=children
        )

    # Check for circularity
    def parents_contain(
        start: Table, probe: Table, seen: Set[Table] = None
    ) -> Tuple[bool, List[Table]]:
        seen = seen or set()
        tdc_ = tdcmap[start]
        if probe in tdc_.parents:
            return True, [start, probe]
        for parent in tdc_.parents:
            if parent in seen:
                continue  # avoid infinite recursion
            seen.add(parent)
            contains_, chain_ = parents_contain(
                start=parent, probe=probe, seen=seen
            )
            if contains_:
                return True, [start] + chain_
        return False, []

    def children_contain(
        start: Table, probe: Table, seen: Set[Table] = None
    ) -> Tuple[bool, List[Table]]:
        seen = seen or set()
        tdc_ = tdcmap[start]
        if probe in tdc_.children:
            return True, [start, probe]
        for child in tdc_.children:
            if child in seen:
                continue  # avoid infinite recursion
            seen.add(child)
            contains_, chain_ = children_contain(
                start=child, probe=probe, seen=seen
            )
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

    def __init__(
        self,
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
        info: Dict[str, Any] = None,
    ) -> None:
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
        self.missing_src_columns: List[str] = missing_src_columns or []
        self.info: Dict[str, Any] = info or {}


# =============================================================================
# suggest_table_order (for merge_db)
# =============================================================================


def suggest_table_order(
    classified_tables: List[TableDependencyClassification],
) -> List[Table]:
    """
    Suggest an order to process tables in, according to precalculated
    dependencies.

    Args:
        classified_tables:
            The tables, with dependency information.

    Returns:
        A list of the tables, sorted into a sensible order.
    """
    # We can't handle a circular situation:
    assert not any(
        tdc.circular for tdc in classified_tables
    ), "Can't handle circular references between tables"
    # Keeping track. With a quasi-arbitrary starting order:
    to_do: Set[TableDependencyClassification] = set(classified_tables)
    tables_done: Set[Table] = set()
    final_order: List[TableDependencyClassification] = []

    # Now, iteratively:
    while to_do:
        suitable = [
            tdc for tdc in to_do if all(p in tables_done for p in tdc.parents)
        ]
        if not suitable:
            raise ValueError("suggest_table_order: Unable to solve")
        suitable.sort(key=lambda ct: ct.table.name)
        final_order.extend(suitable)
        to_do -= set(suitable)
        tables_done.update(tdc.table for tdc in suitable)

    return [tdc.table for tdc in final_order]


# =============================================================================
# merge_db
# =============================================================================


def merge_db(
    base_class: Type,
    src_engine: Engine,
    dst_session: Session,
    allow_missing_src_tables: bool = True,
    allow_missing_src_columns: bool = True,
    translate_fn: Callable[[TranslationContext], None] = None,
    skip_tables: List[TableIdentity] = None,
    only_tables: List[TableIdentity] = None,
    tables_to_keep_pks_for: List[TableIdentity] = None,
    extra_table_dependencies: List[TableDependency] = None,
    skip_table_dependencies: List[TableDependency] = None,
    dummy_run: bool = False,
    info_only: bool = False,
    report_every: int = 1000,
    flush_per_table: bool = True,
    flush_per_record: bool = False,
    commit_with_flush: bool = False,
    commit_at_end: bool = True,
    prevent_eager_load: bool = True,
    trcon_info: Dict[str, Any] = None,
    even_use_alter_relationships: bool = False,
    debug_table_structure: bool = False,
    debug_table_dependencies: bool = False,
    debug_copy_sqla_object: bool = False,
    debug_rewrite_relationships: bool = False,
    use_sqlalchemy_order: bool = True,
) -> None:
    """
    Copies an entire database as far as it is described by ``metadata`` and
    ``base_class``, from SQLAlchemy ORM session ``src_session`` to
    ``dst_session``, and in the process:

    - creates new primary keys at the destination, or raises an error if it
      doesn't know how (typically something like: ``Field 'name' doesn't have a
      default value``)

    - maintains relationships, or raises an error if it doesn't know how

    Basic method:

    - Examines the metadata for the SQLAlchemy ORM base class you provide.

    - Assumes that the tables exist (in the destination).

    - For each table/ORM class found in the metadata:

      - Queries (via the ORM) from the source.

      - For each ORM instance retrieved:

        - Writes information to the destination SQLAlchemy session.

        - If that ORM object has relationships, process them too.

    If a table is missing in the source, then that's OK if and only if
    ``allow_missing_src_tables`` is set. (Similarly with columns and
    ``allow_missing_src_columns``; we ask the ORM to perform a partial load,
    of a subset of attributes only.)

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
            optional list of :class:`TableDependency` objects (q.v.) to include

        skip_table_dependencies:
            optional list of :class:`TableDependency` objects (q.v.) to IGNORE;
            unusual

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

        even_use_alter_relationships:
            Even include relationships with ``use_alter`` set. See SQLAlchemy
            documentation.

        debug_table_structure:
            Debug table structure? Can be long-winded.

        debug_table_dependencies:
            Debug calculating table dependencies?

        debug_copy_sqla_object:
            Debug copying objects?

        debug_rewrite_relationships:
            Debug rewriting ORM relationships?

        use_sqlalchemy_order:
            If true, use the table order suggested by SQLAlchemy. If false,
            calculate our own.
    """

    log.info("merge_db(): starting")
    if dummy_run:
        log.info("Dummy run only; destination will not be changed")

    # Check parameters before we modify them
    if only_tables is not None and not only_tables:
        log.info("... only_tables == []; nothing to do")
        return

    # Finalize parameters
    skip_tables: List[TableIdentity] = skip_tables or []
    only_tables: List[TableIdentity] = only_tables or []
    tables_to_keep_pks_for: List[TableIdentity] = tables_to_keep_pks_for or []
    extra_table_dependencies: List[TableDependency] = (
        extra_table_dependencies or []
    )
    skip_table_dependencies: List[TableDependency] = (
        skip_table_dependencies or []
    )
    trcon_info: Dict[str, Any] = trcon_info or {}

    # We need both Core and ORM for the source.
    # noinspection PyUnresolvedReferences
    metadata: MetaData = base_class.metadata
    src_session: Session = sessionmaker(bind=src_engine, future=True)()
    dst_engine = get_engine_from_session(dst_session)
    tablename_to_ormclass = get_orm_classes_by_table_name_from_base(base_class)

    # Tell all TableIdentity objects about their metadata
    for tilist in [skip_tables, only_tables, tables_to_keep_pks_for]:
        for ti in tilist:
            ti.set_metadata_if_none(metadata)
    for td in extra_table_dependencies:
        td.set_metadata_if_none(metadata)
    for td in skip_table_dependencies:
        td.set_metadata_if_none(metadata)

    # Get all lists of tables as their names
    skip_table_names = [ti.tablename for ti in skip_tables]
    only_table_names = [ti.tablename for ti in only_tables]
    tables_to_keep_pks_for: List[str] = [
        ti.tablename for ti in tables_to_keep_pks_for
    ]
    # ... now all are of type List[str]

    # Safety check: this is an imperfect check for source == destination, but
    # it is fairly easy to pass in the wrong URL, so let's try our best:
    _src_url = get_safe_url_from_engine(src_engine)
    _dst_url = get_safe_url_from_session(dst_session)
    assert (
        _src_url != _dst_url or _src_url == SQLITE_MEMORY_URL
    ), "Source and destination databases are the same!"

    # Check the right tables are present.
    src_tables = sorted(get_table_names(src_engine))
    dst_tables = sorted(list(tablename_to_ormclass.keys()))
    log.debug(f"Source tables: {src_tables!r}")
    log.debug(f"Destination tables: {dst_tables!r}")
    if not allow_missing_src_tables:
        missing_tables = sorted(
            d
            for d in dst_tables
            if d not in src_tables and d not in skip_table_names
        )
        if missing_tables:
            raise RuntimeError(
                "The following tables are missing from the "
                "source database: " + repr(missing_tables)
            )

    table_num = 0
    overall_record_num = 0

    all_dependencies = get_all_dependencies(
        metadata=metadata,
        extra_dependencies=extra_table_dependencies,
        skip_dependencies=skip_table_dependencies,
        debug=debug_table_dependencies,
        even_use_alter=even_use_alter_relationships,
    )
    dep_classifications = classify_tables_by_dependency_type(
        metadata,
        all_dependencies=all_dependencies,
        even_use_alter=even_use_alter_relationships,
    )
    circular = [tdc for tdc in dep_classifications if tdc.circular]
    assert not circular, f"Circular dependencies! {circular!r}"
    all_dependencies.sort()  # cosmetic
    log.debug(
        "All table dependencies: "
        + "; ".join(str(c) for c in dep_classifications)
    )
    tables: List[Table] = list(metadata.tables.values())
    if use_sqlalchemy_order:
        # Very helpfully, MetaData.sorted_tables produces tables in order of
        # relationship dependency ("each table is preceded by all tables which
        # it references");
        # http://docs.sqlalchemy.org/en/latest/core/metadata.html
        # HOWEVER, it only works if you specify ForeignKey relationships
        # explicitly.
        # We can also add in user-specified dependencies, and therefore can do
        # the sorting in one step with sqlalchemy.schema.sort_tables:
        log.debug("Using SQLAlchemy's suggested table order")
        ordered_tables = sort_tables(
            tables,
            extra_dependencies=[
                td.sqla_tuple() for td in extra_table_dependencies
            ],
        )
        # Note that the ordering is NOT NECESSARILY CONSISTENT, though (in that
        # the order of stuff it doesn't care about varies across runs).
    else:
        log.debug("Calculating table order without SQLAlchemy")
        ordered_tables = suggest_table_order(dep_classifications)
    log.info(
        "Processing tables in the order: "
        + repr([table.name for table in ordered_tables])
    )

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
        tc = TranslationContext(
            oldobj=oldobj_,
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
            info=trcon_info,
        )
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
            log.info(f"Skipping table {tablename!r} (as per skip_tables)")
            continue
        if only_table_names and tablename not in only_table_names:
            log.info(f"Ignoring table {tablename!r} (as per only_tables)")
            continue
        if allow_missing_src_tables and tablename not in src_tables:
            log.info(f"Ignoring table {tablename!r} (not in source database)")
            continue
        table_num += 1
        table_record_num = 0

        src_columns = sorted(get_column_names(src_engine, tablename))
        dst_columns = sorted([column.name for column in table.columns])
        missing_columns = sorted(list(set(dst_columns) - set(src_columns)))

        if not allow_missing_src_columns and missing_columns:
            raise RuntimeError(
                f"The following columns are missing from source table "
                f"{tablename!r}: {missing_columns!r}"
            )

        orm_class = tablename_to_ormclass[tablename]
        pk_attrs = get_pk_attrnames(orm_class)
        c2a = colname_to_attrname_dict(orm_class)
        missing_attrs = map_keys_to_values(missing_columns, c2a)
        tdc = [tdc for tdc in dep_classifications if tdc.table == table][0]

        log.info(f"Processing table {tablename!r} via ORM class {orm_class!r}")
        if debug_table_structure:
            log.debug(f"PK attributes: {pk_attrs!r}")
            log.debug(f"Table: {table!r}")
        if debug_table_dependencies:
            log.debug(
                f"Dependencies: parents = {tdc.parent_names!r}; "
                f"children = {tdc.child_names!r}"
            )

        if info_only:
            log.debug("info_only; skipping table contents")
            continue

        def wipe_primary_key(inst: object) -> None:
            # Defined here because it uses pk_attrs
            for attrname in pk_attrs:
                setattr(inst, attrname, None)

        query = src_session.query(orm_class)

        if allow_missing_src_columns and missing_columns:
            src_attrs = map_keys_to_values(src_columns, c2a)
            log.info(
                f"Table {tablename} is missing columns {missing_columns} "
                f"in the source"
            )
            log.debug(
                f"... using only columns {src_columns} "
                f"via attributes {src_attrs}"
            )
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
        #       for relationship in insp.mapper.relationships:  # type: RelationshipProperty  # noqa: E501
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

        instances = list(query.all())
        log.info(f"... processing {len(instances)} records")
        for instance in instances:
            # log.debug(f"Source instance: {instance!r}")
            table_record_num += 1
            overall_record_num += 1
            if table_record_num % report_every == 0:
                log.info(
                    f"... progress{' (DUMMY RUN)' if dummy_run else ''}: "
                    f"on table {table_num} ({tablename}); "
                    f"record {table_record_num} this table; "
                    f"overall record {overall_record_num}"
                )

            if tdc.standalone:
                # Our table has neither parents nor children. We can therefore
                # simply move the instance from one session to the other,
                # blanking primary keys.

                # https://stackoverflow.com/questions/14636192/sqlalchemy-modification-of-detached-object  # noqa: E501
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
                    oldobj,
                    omit_pk=wipe_pk,
                    omit_fk=True,
                    omit_attrs=missing_attrs,
                    debug=debug_copy_sqla_object,
                )

                rewrite_relationships(
                    oldobj,
                    newobj,
                    objmap,
                    debug=debug_rewrite_relationships,
                    skip_table_names=skip_table_names,
                )

                newobj = translate(oldobj, newobj)
                if not newobj:
                    continue  # translate_fn elected to skip it

                if not dummy_run:
                    dst_session.add(newobj)
                    # new PK will be created when session is flushed

                if tdc.is_parent:
                    try:
                        objmap[oldobj] = newobj  # for its children's benefit
                    except KeyError:
                        raise KeyError(
                            f"Missing attribute {oldobj=} in {objmap=}"
                        )

            if flush_per_record:
                flush()

        if flush_per_table:
            flush()

    flush()
    if commit_at_end:
        log.debug("Committing...")
        dst_session.commit()
    log.info("merge_db(): finished")
