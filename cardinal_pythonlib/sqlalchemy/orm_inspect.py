#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/orm_inspect.py

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

import logging
from typing import Dict, Generator, List, Tuple, Type, TYPE_CHECKING, Union

# noinspection PyProtectedMember
from sqlalchemy.ext.declarative.base import _get_immediate_cls_attr
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.base import class_mapper
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.schema import Column, MetaData
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.sql.visitors import VisitableType
from sqlalchemy.util import OrderedProperties

from cardinal_pythonlib.classes import all_subclasses
from cardinal_pythonlib.enumlike import OrderedNamespace
from cardinal_pythonlib.dicts import reversedict
from cardinal_pythonlib.logs import BraceStyleAdapter

if TYPE_CHECKING:
    from sqlalchemy.orm.state import InstanceState
    from sqlalchemy.orm.relationships import RelationshipProperty

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# Creating ORM objects conveniently, etc.
# =============================================================================

def coltype_as_typeengine(coltype: Union[VisitableType,
                                         TypeEngine]) -> TypeEngine:
    """
    To explain: you can specify columns like
        a = Column("a", Integer)
        b = Column("b", Integer())
        c = Column("c", String(length=50))

    isinstance(Integer, TypeEngine)  # False
    isinstance(Integer(), TypeEngine)  # True
    isinstance(String(length=50), TypeEngine)  # True

    type(Integer)  # <class 'sqlalchemy.sql.visitors.VisitableType'>
    type(Integer())  # <class 'sqlalchemy.sql.sqltypes.Integer'>
    type(String)  # <class 'sqlalchemy.sql.visitors.VisitableType'>
    type(String(length=50))  # <class 'sqlalchemy.sql.sqltypes.String'>

    This function coerces things to a TypeEngine.
    """
    if isinstance(coltype, TypeEngine):
        return coltype
    return coltype()  # type: TypeEngine


# =============================================================================
# Mixin to:
# - get plain dictionary-like object (with attributes so we can use x.y rather
#   than x['y']) from an SQLAlchemy ORM object
# - make a nice repr() default, maintaining field order
# =============================================================================

class SqlAlchemyAttrDictMixin(object):
    # See http://stackoverflow.com/questions/2537471
    # but more: http://stackoverflow.com/questions/2441796

    def get_attrdict(self) -> OrderedNamespace:
        """
        Returns what looks like a plain object with the values of the
        SQLAlchemy ORM object.
        """
        # noinspection PyUnresolvedReferences
        columns = self.__table__.columns.keys()
        values = (getattr(self, x) for x in columns)
        zipped = zip(columns, values)
        return OrderedNamespace(zipped)

    def __repr__(self) -> str:
        return "<{classname}({kvp})>".format(
            classname=type(self).__name__,
            kvp=", ".join("{}={}".format(k, repr(v))
                          for k, v in self.get_attrdict().items())
        )

    @classmethod
    def from_attrdict(cls, attrdict: OrderedNamespace) -> object:
        """
        Builds a new instance of the ORM object from values in an attrdict.
        """
        dictionary = attrdict.__dict__
        return cls(**dictionary)


# =============================================================================
# Traverse ORM relationships (SQLAlchemy ORM)
# =============================================================================

def walk(obj, debug: bool = False) -> Generator[object, None, None]:
    """
    Starting with a SQLAlchemy ORM object, this function walks a
    relationship tree, yielding each of the objects once.
    """
    # http://docs.sqlalchemy.org/en/latest/faq/sessions.html#faq-walk-objects
    stack = [obj]
    seen = set()
    while stack:
        obj = stack.pop(0)
        if obj in seen:
            continue
        seen.add(obj)
        if debug:
            log.debug("walk: yielding {!r}", obj)
        yield obj
        insp = inspect(obj)  # type: InstanceState
        for relationship in insp.mapper.relationships:  # type: RelationshipProperty  # noqa
            if debug:
                log.debug("walk: checking relationship {}", relationship)
            related = getattr(obj, relationship.key)
            if relationship.uselist:
                stack.extend(related)
            elif related is not None:
                stack.append(related)


# =============================================================================
# deepcopy an SQLAlchemy object
# =============================================================================
# Use case: object X is in the database; we want to clone it to object Y,
# which we can then save to the database, i.e. copying all SQLAlchemy field
# attributes of X except its PK. We also want it to copy anything that is
# dependent upon X, i.e. traverse relationships.
#
# https://groups.google.com/forum/#!topic/sqlalchemy/wb2M_oYkQdY
# https://groups.google.com/forum/#!searchin/sqlalchemy/cascade%7Csort:date/sqlalchemy/eIOkkXwJ-Ms/JLnpI2wJAAAJ  # noqa

def copy_sqla_object(obj: object,
                     omit_fk: bool = True,
                     omit_pk: bool = True,
                     omit_attrs: List[str] = None,
                     debug: bool = True) -> object:
    """
    Given an SQLAlchemy object, creates a new object (FOR WHICH THE OBJECT
    MUST SUPPORT CREATION USING __init__() WITH NO PARAMETERS), and copies
    across all attributes, omitting PKs (by default), FKs (by default), and
    relationship attributes.
    """
    omit_attrs = omit_attrs or []  # type: List[str]
    cls = type(obj)
    mapper = class_mapper(cls)
    newobj = cls()  # not: cls.__new__(cls)
    rel_keys = set([c.key for c in mapper.relationships])
    prohibited = rel_keys
    if omit_pk:
        pk_keys = set([c.key for c in mapper.primary_key])
        prohibited |= pk_keys
    if omit_fk:
        fk_keys = set([c.key for c in mapper.columns if c.foreign_keys])
        prohibited |= fk_keys
    prohibited |= set(omit_attrs)
    if debug:
        log.debug("copy_sqla_object: skipping: {}", prohibited)
    for k in [p.key for p in mapper.iterate_properties
              if p.key not in prohibited]:
        try:
            value = getattr(obj, k)
            if debug:
                log.debug("copy_sqla_object: processing attribute {} = {}",
                          k, value)
            setattr(newobj, k, value)
        except AttributeError:
            if debug:
                log.debug("copy_sqla_object: failed attribute {}", k)
            pass
    return newobj


def rewrite_relationships(oldobj: object,
                          newobj: object,
                          objmap: Dict[object, object],
                          debug: bool = True,
                          skip_table_names: List[str] = None) -> None:
    """
    A utility function only.
    Used in copying objects between SQLAlchemy sessions.

    Both "oldobj" and "newobj" are SQLAlchemy instances.
    The instance "newobj" is already a copy of "oldobj" but we wish to rewrite
    its relationships, according the the map "objmap", which maps old to new
    objects.
    """
    skip_table_names = skip_table_names or []  # type: List[str]
    insp = inspect(oldobj)  # type: InstanceState
    # insp.mapper.relationships is of type
    # sqlalchemy.utils._collections.ImmutableProperties, which is basically
    # a sort of AttrDict.
    for attrname_rel in insp.mapper.relationships.items():  # type: Tuple[str, RelationshipProperty]  # noqa
        attrname = attrname_rel[0]
        rel_prop = attrname_rel[1]
        if rel_prop.viewonly:
            if debug:
                log.debug("Skipping viewonly relationship")
            continue  # don't attempt to write viewonly relationships  # noqa
        related_class = rel_prop.mapper.class_
        related_table_name = related_class.__tablename__  # type: str
        if related_table_name in skip_table_names:
            if debug:
                log.debug("Skipping relationship for related table {!r}",
                          related_table_name)
            continue
        # The relationship is an abstract object (so getting the
        # relationship from the old object and from the new, with e.g.
        # newrel = newinsp.mapper.relationships[oldrel.key],
        # yield the same object. All we need from it is the key name.
        #       rel_key = rel.key  # type: str
        # ... but also available from the mapper as attrname, above
        related_old = getattr(oldobj, attrname)
        if rel_prop.uselist:
            related_new = [objmap[r] for r in related_old]
        elif related_old is not None:
            related_new = objmap[related_old]
        else:
            related_new = None
        if debug:
            log.debug("rewrite_relationships: relationship {} -> {}",
                      attrname, related_new)
        setattr(newobj, attrname, related_new)


def deepcopy_sqla_object(startobj: object, session: Session,
                         flush: bool = True, debug: bool = True) -> object:
    """
    Makes a copy of the object, inserting it into "session".
    For this to succeed, the object must take a __init__ call with no
    arguments. (We can't specify the required args/kwargs, since we are copying
    a tree of arbitrary objects.)
    """
    objmap = {}  # keys = old objects, values = new objects
    if debug:
        log.debug("deepcopy_sqla_object: pass 1: create new objects")

    # Pass 1: iterate through all objects. (Can't guarantee to get
    # relationships correct until we've done this, since we don't know whether
    # or where the "root" of the PK tree is.)
    for oldobj in walk(startobj, debug=debug):
        if debug:
            log.debug("deepcopy_sqla_object: copying {}", oldobj)
        newobj = copy_sqla_object(oldobj, omit_pk=True, omit_fk=True)
        # Don't insert the new object into the session here; it may trigger
        # an autoflush as the relationships are queried, and the new objects
        # are not ready for insertion yet (as their relationships aren't set).
        # Not also the session.no_autoflush option:
        # "sqlalchemy.exc.OperationalError: (raised as a result of Query-
        # invoked autoflush; consider using a session.no_autoflush block if
        # this flush is occurring prematurely)..."
        objmap[oldobj] = newobj

    # Pass 2: set all relationship properties.
    if debug:
        log.debug("deepcopy_sqla_object: pass 2: set relationships")
    for oldobj, newobj in objmap.items():
        if debug:
            log.debug("deepcopy_sqla_object: newobj: {}", newobj)
        rewrite_relationships(oldobj, newobj, objmap, debug=debug)

    # Now we can do session insert.
    if debug:
        log.debug("deepcopy_sqla_object: pass 3: insert into session")
    for newobj in objmap.values():
        session.add(newobj)

    # Done
    if debug:
        log.debug("deepcopy_sqla_object: done")
    if flush:
        session.flush()
    return objmap[startobj]  # returns the new object matching startobj


# =============================================================================
# Get Columns from an ORM instance
# =============================================================================

def gen_columns(obj) -> Generator[Tuple[str, Column], None, None]:
    """
    Yields tuples of (attr_name, Column) from an SQLAlchemy ORM object
    instance. ALSO works with the corresponding SQLAlchemy ORM class. Examples:

        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.sql.schema import Column
        from sqlalchemy.sql.sqltypes import Integer

        Base = declarative_base()

        class MyClass(Base):
            __tablename__ = "mytable"
            pk = Column("pk", Integer, primary_key=True, autoincrement=True)
            a = Column("a", Integer)

        x = MyClass()

        list(gen_columns(x))
        list(gen_columns(MyClass))

    """
    mapper = obj.__mapper__  # type: Mapper
    assert mapper, "gen_columns called on {!r} which is not an " \
                   "SQLAlchemy ORM object".format(obj)
    colmap = mapper.columns  # type: OrderedProperties
    if not colmap:
        return
    for attrname, column in colmap.items():
        # NB: column.name is the SQL column name, not the attribute name
        yield attrname, column
    # Don't bother using
    #   cls = obj.__class_
    #   for attrname in dir(cls):
    #       cls_attr = getattr(cls, attrname)
    #       # ... because, for columns, these will all be instances of
    #       # sqlalchemy.orm.attributes.InstrumentedAttribute.


def get_pk_attrnames(obj) -> List[str]:
    return [attrname
            for attrname, column in gen_columns(obj)
            if column.primary_key]


def gen_columns_for_uninstrumented_class(cls: Type) \
        -> Generator[Tuple[str, Column], None, None]:
    """
    Generate (attr_name, Column) tuples from an UNINSTRUMENTED class, i.e. one
    that does not inherit from declarative_base(). Use this for mixins of that
    kind.

    SUBOPTIMAL. May produce warnings like:
    SAWarning: Unmanaged access of declarative attribute id from non-mapped class GenericTabletRecordMixin  # noqa

    Try to use gen_columns() instead.
    """
    for attrname in dir(cls):
        potential_column = getattr(cls, attrname)
        if isinstance(potential_column, Column):
            yield attrname, potential_column


def attrname_to_colname_dict(cls) -> Dict[str, str]:
    attr_col = {}  # type: Dict[str, str]
    for attrname, column in gen_columns(cls):
        attr_col[attrname] = column.name
    return attr_col


def colname_to_attrname_dict(cls) -> Dict[str, str]:
    return reversedict(attrname_to_colname_dict(cls))


# =============================================================================
# Inspect ORM objects (SQLAlchemy ORM)
# =============================================================================

def get_orm_columns(cls: Type) -> List[Column]:
    """
    Gets Column objects from an SQLAlchemy ORM class.
    Does not provide their attribute names.
    """
    mapper = inspect(cls)  # type: Mapper
    # ... returns InstanceState if called with an ORM object
    #     http://docs.sqlalchemy.org/en/latest/orm/session_state_management.html#session-object-states  # noqa
    # ... returns Mapper if called with an ORM class
    #     http://docs.sqlalchemy.org/en/latest/orm/mapping_api.html#sqlalchemy.orm.mapper.Mapper  # noqa
    colmap = mapper.columns  # type: OrderedProperties
    return colmap.values()


def get_orm_column_names(cls: Type, sort: bool = False) -> List[str]:
    colnames = [col.name for col in get_orm_columns(cls)]
    return sorted(colnames) if sort else colnames


# =============================================================================
# Inspect metadata (SQLAlchemy ORM)
# =============================================================================

def get_table_names_from_metadata(metadata: MetaData) -> List[str]:
    return [table.name for table in metadata.tables.values()]


def get_orm_classes_from_base(base: Type) -> List[Type]:
    orm_classes = []  # type: List[Type]
    for cls in all_subclasses(base):
        if _get_immediate_cls_attr(cls, '__abstract__', strict=True):
            # This is SQLAlchemy's own way of detecting abstract classes; see
            # sqlalchemy.ext.declarative.base
            continue
        orm_classes.append(cls)
    return orm_classes


def get_orm_classes_by_table_name_from_base(base: Type) -> Dict[str, Type]:
    """
    Given the SQLAlchemy ORM base class, returns a dictionary whose keys are
    table names and whose values are ORM classes.
    """
    # noinspection PyUnresolvedReferences
    return {cls.__tablename__: cls for cls in get_orm_classes_from_base(base)}
