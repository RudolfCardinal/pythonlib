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
from typing import Generator, List, Tuple, Type, Union

from sqlalchemy.inspection import inspect
from sqlalchemy.orm.base import class_mapper
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.sql.visitors import VisitableType
from sqlalchemy.util import OrderedProperties

from cardinal_pythonlib.enumlike import OrderedNamespace

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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
# deepcopy an SQLAlchemy object
# =============================================================================
# Use case: object X is in the database; we want to clone it to object Y,
# which we can then save to the database, i.e. copying all SQLAlchemy field
# attributes of X except its PK. We also want it to copy anything that is
# dependent upon X, i.e. traverse relationships.
#
# https://groups.google.com/forum/#!topic/sqlalchemy/wb2M_oYkQdY
# https://groups.google.com/forum/#!searchin/sqlalchemy/cascade%7Csort:date/sqlalchemy/eIOkkXwJ-Ms/JLnpI2wJAAAJ  # noqa

def walk(obj) -> Generator[object, None, None]:
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
        else:
            seen.add(obj)
            yield obj
        insp = inspect(obj)
        for relationship in insp.mapper.relationships:
            related = getattr(obj, relationship.key)
            if relationship.uselist:
                stack.extend(related)
            elif related is not None:
                stack.append(related)


def copy_sqla_object(obj: object, omit_fk: bool = True) -> object:
    """
    Given an SQLAlchemy object, creates a new object (FOR WHICH THE OBJECT
    MUST SUPPORT CREATION USING __init__() WITH NO PARAMETERS), and copies
    across all attributes, omitting PKs, FKs (by default), and relationship
    attributes.
    """
    cls = type(obj)
    mapper = class_mapper(cls)
    newobj = cls()  # not: cls.__new__(cls)
    pk_keys = set([c.key for c in mapper.primary_key])
    rel_keys = set([c.key for c in mapper.relationships])
    prohibited = pk_keys | rel_keys
    if omit_fk:
        fk_keys = set([c.key for c in mapper.columns if c.foreign_keys])
        prohibited |= fk_keys
    log.debug("copy_sqla_object: skipping: {}".format(prohibited))
    for k in [p.key for p in mapper.iterate_properties
              if p.key not in prohibited]:
        try:
            value = getattr(obj, k)
            log.debug("copy_sqla_object: processing attribute {} = {}".format(
                k, value))
            setattr(newobj, k, value)
        except AttributeError:
            log.debug("copy_sqla_object: failed attribute {}".format(k))
            pass
    return newobj


def deepcopy_sqla_object(startobj: object, session: Session,
                         flush: bool = True) -> object:
    """
    For this to succeed, the object must take a __init__ call with no
    arguments. (We can't specify the required args/kwargs, since we are copying
    a tree of arbitrary objects.)
    """
    objmap = {}  # keys = old objects, values = new objects
    log.debug("deepcopy_sqla_object: pass 1: create new objects")
    # Pass 1: iterate through all objects. (Can't guarantee to get
    # relationships correct until we've done this, since we don't know whether
    # or where the "root" of the PK tree is.)
    stack = [startobj]
    while stack:
        oldobj = stack.pop(0)
        if oldobj in objmap:  # already seen
            continue
        log.debug("deepcopy_sqla_object: copying {}".format(oldobj))
        newobj = copy_sqla_object(oldobj)
        # Don't insert the new object into the session here; it may trigger
        # an autoflush as the relationships are queried, and the new objects
        # are not ready for insertion yet (as their relationships aren't set).
        # Not also the session.no_autoflush option:
        # "sqlalchemy.exc.OperationalError: (raised as a result of Query-
        # invoked autoflush; consider using a session.no_autoflush block if
        # this flush is occurring prematurely)..."
        objmap[oldobj] = newobj
        insp = inspect(oldobj)
        for relationship in insp.mapper.relationships:
            log.debug("deepcopy_sqla_object: ... relationship: {}".format(
                relationship))
            related = getattr(oldobj, relationship.key)
            if relationship.uselist:
                stack.extend(related)
            elif related is not None:
                stack.append(related)
    # Pass 2: set all relationship properties.
    log.debug("deepcopy_sqla_object: pass 2: set relationships")
    for oldobj, newobj in objmap.items():
        log.debug("deepcopy_sqla_object: newobj: {}".format(newobj))
        insp = inspect(oldobj)
        # insp.mapper.relationships is of type
        # sqlalchemy.utils._collections.ImmutableProperties, which is basically
        # a sort of AttrDict.
        for relationship in insp.mapper.relationships:
            # The relationship is an abstract object (so getting the
            # relationship from the old object and from the new, with e.g.
            # newrel = newinsp.mapper.relationships[oldrel.key],
            # yield the same object. All we need from it is the key name.
            log.debug("deepcopy_sqla_object: ... relationship: {}".format(
                relationship.key))
            related_old = getattr(oldobj, relationship.key)
            if relationship.uselist:
                related_new = [objmap[r] for r in related_old]
            elif related_old is not None:
                related_new = objmap[related_old]
            else:
                related_new = None
            log.debug("deepcopy_sqla_object: ... ... adding: {}".format(
                related_new))
            setattr(newobj, relationship.key, related_new)
    # Now we can do session insert.
    log.debug("deepcopy_sqla_object: pass 3: insert into session")
    for newobj in objmap.values():
        session.add(newobj)
    # Done
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
    instance.
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
