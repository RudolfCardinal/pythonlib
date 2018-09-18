#!/usr/bin/env python
# cardinal_pythonlib/json/serialize.py

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

**Functions to make it easy to serialize Python objects to/from JSON.**

See ``notes_on_pickle_json.txt``.

The standard Python representation used internally is a dictionary like this:

.. code-block:: python

    {
        __type__: 'MyClass',
        args: [some, positional, args],
        kwargs: {
            'some': 1,
            'named': 'hello',
            'args': [2, 3, 4],
        }
    }

We will call this an ``InitDict``.

Sometimes positional arguments aren't necessary and it's convenient to work
also with the simpler dictionary:

.. code-block:: python

    {
        'some': 1,
        'named': 'hello',
        'args': [2, 3, 4],
    }

... which we'll call a ``KwargsDict``.

"""

import datetime
from enum import Enum
import json
import logging
import pprint
import sys
from typing import Any, Callable, Dict, List, TextIO, Tuple, Type

import pendulum
from pendulum import Date, DateTime
# from pendulum.tz.timezone import Timezone
# from pendulum.tz.timezone_info import TimezoneInfo
# from pendulum.tz.transition import Transition

from cardinal_pythonlib.reprfunc import auto_repr

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

Instance = Any
ClassType = Type[object]

InitDict = Dict[str, Any]
KwargsDict = Dict[str, Any]
ArgsList = List[Any]

ArgsKwargsTuple = Tuple[ArgsList, KwargsDict]

InstanceToDictFnType = Callable[[Instance], Dict]
DictToInstanceFnType = Callable[[Dict, ClassType], Instance]
DefaultFactoryFnType = Callable[[], Instance]
InitArgsKwargsFnType = Callable[[Instance], ArgsKwargsTuple]
InitKwargsFnType = Callable[[Instance], KwargsDict]
InstanceToInitDictFnType = Callable[[Instance], InitDict]

# =============================================================================
# Constants for external use
# =============================================================================

METHOD_NO_ARGS = 'no_args'
METHOD_SIMPLE = 'simple'
METHOD_STRIP_UNDERSCORE = 'strip_underscore'
METHOD_PROVIDES_INIT_ARGS_KWARGS = 'provides_init_args_kwargs'
METHOD_PROVIDES_INIT_KWARGS = 'provides_init_kwargs'

# =============================================================================
# Constants for internal use
# =============================================================================

DEBUG = False

ARGS_LABEL = 'args'
KWARGS_LABEL = 'kwargs'
TYPE_LABEL = '__type__'

INIT_ARGS_KWARGS_FN_NAME = 'init_args_kwargs'
INIT_KWARGS_FN_NAME = 'init_kwargs'


# =============================================================================
# Simple dictionary manipulation
# =============================================================================

def args_kwargs_to_initdict(args: ArgsList, kwargs: KwargsDict) -> InitDict:
    """
    Converts a set of ``args`` and ``kwargs`` to an ``InitDict``.
    """
    return {ARGS_LABEL: args,
            KWARGS_LABEL: kwargs}


def kwargs_to_initdict(kwargs: KwargsDict) -> InitDict:
    """
    Converts a set of ``kwargs`` to an ``InitDict``.
    """
    return {ARGS_LABEL: [],
            KWARGS_LABEL: kwargs}


# noinspection PyUnusedLocal
def obj_with_no_args_to_init_dict(obj: Any) -> InitDict:
    """
    Creates an empty ``InitDict``, for use with an object that takes no
    arguments at creation.
    """

    return {ARGS_LABEL: [],
            KWARGS_LABEL: {}}


def strip_leading_underscores_from_keys(d: Dict) -> Dict:
    """
    Clones a dictionary, removing leading underscores from key names.
    Raises ``ValueError`` if this causes an attribute conflict.
    """
    newdict = {}
    for k, v in d.items():
        if k.startswith('_'):
            k = k[1:]
            if k in newdict:
                raise ValueError("Attribute conflict: _{k}, {k}".format(k=k))
        newdict[k] = v
    return newdict


def verify_initdict(initdict: InitDict) -> None:
    """
    Ensures that its parameter is a proper ``InitDict``, or raises
    ``ValueError``.
    """
    if (not isinstance(initdict, dict) or
            ARGS_LABEL not in initdict or
            KWARGS_LABEL not in initdict):
        raise ValueError("Not an InitDict dictionary")


# =============================================================================
# InitDict -> class instance
# =============================================================================

def initdict_to_instance(d: InitDict, cls: ClassType) -> Any:
    """
    Converse of simple_to_dict().
    Given that JSON dictionary, we will end up re-instantiating the class with

    .. code-block:: python

        d = {'a': 1, 'b': 2, 'c': 3}
        new_x = SimpleClass(**d)

    We'll also support arbitrary creation, by using both ``*args`` and
    ``**kwargs``.
    """
    args = d.get(ARGS_LABEL, [])
    kwargs = d.get(KWARGS_LABEL, {})
    # noinspection PyArgumentList
    return cls(*args, **kwargs)


# =============================================================================
# Class instance -> InitDict, in various ways
# =============================================================================

def instance_to_initdict_simple(obj: Any) -> InitDict:
    """
    For use when object attributes (found in ``obj.__dict__``) should be mapped
    directly to the serialized JSON dictionary. Typically used for classes
    like:

    .. code-block:: python

        class SimpleClass(object):
            def __init__(self, a, b, c):
                self.a = a
                self.b = b
                self.c = c

            Here, after

                x = SimpleClass(a=1, b=2, c=3)

            we will find that

                x.__dict__ == {'a': 1, 'b': 2, 'c': 3}

    and that dictionary is a reasonable thing to serialize to JSON as keyword
    arguments.

    We'll also support arbitrary creation, by using both ``*args`` and
    ``**kwargs``. We may not use this format much, but it has the advantage of
    being an arbitrarily correct format for Python class construction.
    """
    return kwargs_to_initdict(obj.__dict__)


def instance_to_initdict_stripping_underscores(obj: Instance) -> InitDict:
    """
    This is appropriate when a class uses a ``'_'`` prefix for all its
    ``__init__`` parameters, like this:

    .. code-block:: python

        class UnderscoreClass(object):
            def __init__(self, a, b, c):
                self._a = a
                self._b = b
                self._c = c

    Here, after

    .. code-block:: python

        y = UnderscoreClass(a=1, b=2, c=3)

    we will find that

    .. code-block:: python

        y.__dict__ == {'_a': 1, '_b': 2, '_c': 3}

    but we would like to serialize the parameters we can pass back to
    ``__init__``, by removing the leading underscores, like this:

    .. code-block:: python

        {'a': 1, 'b': 2, 'c': 3}
    """
    return kwargs_to_initdict(
        strip_leading_underscores_from_keys(obj.__dict__))


def wrap_kwargs_to_initdict(init_kwargs_fn: InitKwargsFnType,
                            typename: str,
                            check_result: bool = True) \
        -> InstanceToInitDictFnType:
    """
    Wraps a function producing a ``KwargsDict``, making it into a function
    producing an ``InitDict``.
    """
    def wrapper(obj: Instance) -> InitDict:
        result = init_kwargs_fn(obj)
        if check_result:
            if not isinstance(result, dict):
                raise ValueError(
                    "Class {} failed to provide a kwargs dict and "
                    "provided instead: {}".format(typename, repr(result)))
        return kwargs_to_initdict(init_kwargs_fn(obj))

    return wrapper


def wrap_args_kwargs_to_initdict(init_args_kwargs_fn: InitArgsKwargsFnType,
                                 typename: str,
                                 check_result: bool = True) \
        -> InstanceToInitDictFnType:
    """
    Wraps a function producing a ``KwargsDict``, making it into a function
    producing an ``InitDict``.
    """
    def wrapper(obj: Instance) -> InitDict:
        result = init_args_kwargs_fn(obj)
        if check_result:
            if (not isinstance(result, tuple) or
                    not len(result) == 2 or
                    not isinstance(result[0], list) or
                    not isinstance(result[1], dict)):
                raise ValueError(
                    "Class {} failed to provide an (args, kwargs) tuple and "
                    "provided instead: {}".format(typename, repr(result)))
        return args_kwargs_to_initdict(*result)

    return wrapper


# =============================================================================
# Function to make custom instance -> InitDict functions
# =============================================================================

def make_instance_to_initdict(attributes: List[str]) -> InstanceToDictFnType:
    """
    Returns a function that takes an object (instance) and produces an
    ``InitDict`` enabling its re-creation.
    """
    def custom_instance_to_initdict(x: Instance) -> InitDict:
        kwargs = {}
        for a in attributes:
            kwargs[a] = getattr(x, a)
        return kwargs_to_initdict(kwargs)

    return custom_instance_to_initdict


# =============================================================================
# Describe how a Python class should be serialized to/from JSON
# =============================================================================

class JsonDescriptor(object):
    """
    Describe how a Python class should be serialized to/from JSON.
    """
    def __init__(self,
                 typename: str,
                 obj_to_dict_fn: InstanceToDictFnType,
                 dict_to_obj_fn: DictToInstanceFnType,
                 cls: ClassType,
                 default_factory: DefaultFactoryFnType = None) -> None:
        self._typename = typename
        self._obj_to_dict_fn = obj_to_dict_fn
        self._dict_to_obj_fn = dict_to_obj_fn
        self._cls = cls
        self._default_factory = default_factory

    def to_dict(self, obj: Instance) -> Dict:
        return self._obj_to_dict_fn(obj)

    def to_obj(self, d: Dict) -> Instance:
        # noinspection PyBroadException
        try:
            return self._dict_to_obj_fn(d, self._cls)
        except Exception as err:
            log.warning(
                "Failed to deserialize object of type {t}; exception was {e}; "
                "dict was {d}; will use default factory instead".format(
                    t=self._typename, e=repr(err), d=repr(d)))
            if self._default_factory:
                return self._default_factory()
            else:
                return None

    def __repr__(self):
        return (
            "<{qualname}("
            "typename={typename}, "
            "obj_to_dict_fn={obj_to_dict_fn}, "
            "dict_to_obj_fn={dict_to_obj_fn}, "
            "cls={cls}, "
            "default_factory={default_factory}"
            ") at {addr}>".format(
                qualname=self.__class__.__qualname__,
                typename=repr(self._typename),
                obj_to_dict_fn=repr(self._obj_to_dict_fn),
                dict_to_obj_fn=repr(self._dict_to_obj_fn),
                cls=repr(self._cls),
                default_factory=repr(self._default_factory),
                addr=hex(id(self)),
            )
        )


# =============================================================================
# Maintain a record of how several classes should be serialized
# =============================================================================

TYPE_MAP = {}  # type: Dict[str, JsonDescriptor]


def register_class_for_json(
        cls: ClassType,
        method: str = METHOD_SIMPLE,
        obj_to_dict_fn: InstanceToDictFnType = None,
        dict_to_obj_fn: DictToInstanceFnType = initdict_to_instance,
        default_factory: DefaultFactoryFnType = None) -> None:
    """
    Registers the class cls for JSON serialization.

    - If both ``obj_to_dict_fn`` and dict_to_obj_fn are registered, the
      framework uses these to convert instances of the class to/from Python
      dictionaries, which are in turn serialized to JSON.

    - Otherwise:

      .. code-block:: python

        if method == 'simple':
            # ... uses simple_to_dict and simple_from_dict (q.v.)

        if method == 'strip_underscore':
            # ... uses strip_underscore_to_dict and simple_from_dict (q.v.)
    """
    typename = cls.__qualname__  # preferable to __name__
    # ... __name__ looks like "Thing" and is ambiguous
    # ... __qualname__ looks like "my.module.Thing" and is not
    if obj_to_dict_fn and dict_to_obj_fn:
        descriptor = JsonDescriptor(
            typename=typename,
            obj_to_dict_fn=obj_to_dict_fn,
            dict_to_obj_fn=dict_to_obj_fn,
            cls=cls,
            default_factory=default_factory)
    elif method == METHOD_SIMPLE:
        descriptor = JsonDescriptor(
            typename=typename,
            obj_to_dict_fn=instance_to_initdict_simple,
            dict_to_obj_fn=initdict_to_instance,
            cls=cls,
            default_factory=default_factory)
    elif method == METHOD_STRIP_UNDERSCORE:
        descriptor = JsonDescriptor(
            typename=typename,
            obj_to_dict_fn=instance_to_initdict_stripping_underscores,
            dict_to_obj_fn=initdict_to_instance,
            cls=cls,
            default_factory=default_factory)
    else:
        raise ValueError("Unknown method, and functions not fully specified")
    global TYPE_MAP
    TYPE_MAP[typename] = descriptor


def register_for_json(*args, **kwargs) -> Any:
    """
    Class decorator to register classes with our JSON system.

    - If method is ``'provides_init_args_kwargs'``, the class provides a
      function

      .. code-block:: python

        def init_args_kwargs(self) -> Tuple[List[Any], Dict[str, Any]]

      that returns an ``(args, kwargs)`` tuple, suitable for passing to its
      ``__init__()`` function as ``__init__(*args, **kwargs)``.

    - If method is ``'provides_init_kwargs'``, the class provides a function

      .. code-block:: python

        def init_kwargs(self) -> Dict

      that returns a dictionary ``kwargs`` suitable for passing to its
      ``__init__()`` function as ``__init__(**kwargs)``.

    - Otherwise, the method argument is as for ``register_class_for_json()``.

    Usage looks like:

    .. code-block:: python

        @register_for_json(method=METHOD_STRIP_UNDERSCORE)
        class TableId(object):
            def __init__(self, db: str = '', schema: str = '',
                         table: str = '') -> None:
                self._db = db
                self._schema = schema
                self._table = table

    """
    if DEBUG:
        print("register_for_json: args = {}".format(repr(args)))
        print("register_for_json: kwargs = {}".format(repr(kwargs)))

    # http://stackoverflow.com/questions/653368/how-to-create-a-python-decorator-that-can-be-used-either-with-or-without-paramet  # noqa
    # In brief,
    #   @decorator
    #   x
    #
    # means
    #   x = decorator(x)
    #
    # so
    #   @decorator(args)
    #   x
    #
    # means
    #   x = decorator(args)(x)

    if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
        if DEBUG:
            print("... called as @register_for_json")
        # called as @decorator
        # ... the single argument is the class itself, e.g. Thing in:
        #   @decorator
        #   class Thing(object):
        #       # ...
        # ... e.g.:
        #   args = (<class '__main__.unit_tests.<locals>.SimpleThing'>,)
        #   kwargs = {}
        cls = args[0]  # type: ClassType
        register_class_for_json(cls, method=METHOD_SIMPLE)
        return cls

    # Otherwise:
    if DEBUG:
        print("... called as @register_for_json(*args, **kwargs)")
    # called as @decorator(*args, **kwargs)
    # ... e.g.:
    #   args = ()
    #   kwargs = {'method': 'provides_to_init_args_kwargs_dict'}
    method = kwargs.pop('method', METHOD_SIMPLE)  # type: str
    obj_to_dict_fn = kwargs.pop('obj_to_dict_fn', None)  # type: InstanceToDictFnType  # noqa
    dict_to_obj_fn = kwargs.pop('dict_to_obj_fn', initdict_to_instance)  # type: DictToInstanceFnType  # noqa
    default_factory = kwargs.pop('default_factory', None)  # type: DefaultFactoryFnType  # noqa
    check_result = kwargs.pop('check_results', True)  # type: bool

    def register_json_class(cls_: ClassType) -> ClassType:
        odf = obj_to_dict_fn
        dof = dict_to_obj_fn
        if method == METHOD_PROVIDES_INIT_ARGS_KWARGS:
            if hasattr(cls_, INIT_ARGS_KWARGS_FN_NAME):
                odf = wrap_args_kwargs_to_initdict(
                    getattr(cls_, INIT_ARGS_KWARGS_FN_NAME),
                    typename=cls_.__qualname__,
                    check_result=check_result
                )
            else:
                raise ValueError(
                    "Class type {} does not provide function {}".format(
                        cls_, INIT_ARGS_KWARGS_FN_NAME))
        elif method == METHOD_PROVIDES_INIT_KWARGS:
            if hasattr(cls_, INIT_KWARGS_FN_NAME):
                odf = wrap_kwargs_to_initdict(
                    getattr(cls_, INIT_KWARGS_FN_NAME),
                    typename=cls_.__qualname__,
                    check_result=check_result
                )
            else:
                raise ValueError(
                    "Class type {} does not provide function {}".format(
                        cls_, INIT_KWARGS_FN_NAME))
        elif method == METHOD_NO_ARGS:
            odf = obj_with_no_args_to_init_dict
        register_class_for_json(cls_,
                                method=method,
                                obj_to_dict_fn=odf,
                                dict_to_obj_fn=dof,
                                default_factory=default_factory)
        return cls_

    return register_json_class


def dump_map(file: TextIO = sys.stdout) -> None:
    """
    Prints the JSON "registered types" map to the specified file.
    """
    pp = pprint.PrettyPrinter(indent=4, stream=file)
    print("Type map: ", file=file)
    pp.pprint(TYPE_MAP)


# =============================================================================
# Hooks to implement the JSON encoding/decoding
# =============================================================================

class JsonClassEncoder(json.JSONEncoder):
    """
    Provides a JSON encoder whose ``default`` method encodes a Python object
    to JSON with reference to our ``TYPE_MAP``.
    """
    def default(self, obj: Instance) -> Any:
        typename = type(obj).__qualname__  # preferable to __name__, as above
        if typename in TYPE_MAP:
            descriptor = TYPE_MAP[typename]
            d = descriptor.to_dict(obj)
            if TYPE_LABEL in d:
                raise ValueError("Class already has attribute: " + TYPE_LABEL)
            d[TYPE_LABEL] = typename
            if DEBUG:
                log.debug("Serializing {} -> {}".format(repr(obj), repr(d)))
            return d
        # Otherwise, nothing that we know about:
        return super().default(obj)


def json_class_decoder_hook(d: Dict) -> Any:
    """
    Provides a JSON decoder that converts dictionaries to Python objects if
    suitable methods are found in our ``TYPE_MAP``.
    """
    if TYPE_LABEL in d:
        typename = d.get(TYPE_LABEL)
        if typename in TYPE_MAP:
            if DEBUG:
                log.debug("Deserializing: {}".format(repr(d)))
            d.pop(TYPE_LABEL)
            descriptor = TYPE_MAP[typename]
            obj = descriptor.to_obj(d)
            if DEBUG:
                log.debug("... to: {}".format(repr(obj)))
            return obj
    return d


# =============================================================================
# Functions for end users
# =============================================================================

def json_encode(obj: Instance, **kwargs) -> str:
    """
    Encodes an object to JSON using our custom encoder.

    The ``**kwargs`` can be used to pass things like ``'indent'``, for
    formatting.
    """
    return json.dumps(obj, cls=JsonClassEncoder, **kwargs)


def json_decode(s: str) -> Any:
    """
    Decodes an object from JSON using our custom decoder.
    """
    try:
        return json.JSONDecoder(object_hook=json_class_decoder_hook).decode(s)
    except json.JSONDecodeError:
        log.warning("Failed to decode JSON (returning None): {}".format(
            repr(s)))
        return None


# =============================================================================
# Implement JSON translation for common types
# =============================================================================

# -----------------------------------------------------------------------------
# datetime.date
# -----------------------------------------------------------------------------

register_class_for_json(
    cls=datetime.date,
    obj_to_dict_fn=make_instance_to_initdict(['year', 'month', 'day'])
)

# -----------------------------------------------------------------------------
# datetime.datetime
# -----------------------------------------------------------------------------

register_class_for_json(
    cls=datetime.datetime,
    obj_to_dict_fn=make_instance_to_initdict([
        'year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond',
        'tzinfo'
    ])
)

# -----------------------------------------------------------------------------
# datetime.timedelta
# -----------------------------------------------------------------------------

# Note in passing: the repr() of datetime.date and datetime.datetime look like
# 'datetime.date(...)' only because their repr() function explicitly does
# 'datetime.' + self.__class__.__name__; there's no way, it seems, to get
# that or __qualname__ to add the prefix automatically.
register_class_for_json(
    cls=datetime.timedelta,
    obj_to_dict_fn=make_instance_to_initdict([
        'days', 'seconds', 'microseconds'
    ])
)


# -----------------------------------------------------------------------------
# enum.Enum
# -----------------------------------------------------------------------------
# Since this is a family of classes, we provide a decorator.

def enum_to_dict_fn(e: Enum) -> Dict[str, Any]:
    """
    Converts an ``Enum`` to a ``dict``.
    """
    return {
        'name': e.name
    }


def dict_to_enum_fn(d: Dict[str, Any], enum_class: Type[Enum]) -> Enum:
    """
    Converts an ``dict`` to a ``Enum``.
    """
    return enum_class[d['name']]


def register_enum_for_json(*args, **kwargs) -> Any:
    """
    Class decorator to register ``Enum``-derived classes with our JSON system.
    See comments/help for ``@register_for_json``, above.
    """
    if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
        # called as @register_enum_for_json
        cls = args[0]  # type: ClassType
        register_class_for_json(
            cls,
            obj_to_dict_fn=enum_to_dict_fn,
            dict_to_obj_fn=dict_to_enum_fn
        )
        return cls
    else:
        # called as @register_enum_for_json(*args, **kwargs)
        raise AssertionError("Use as plain @register_enum_for_json, "
                             "without arguments")


# -----------------------------------------------------------------------------
# pendulum.DateTime (formerly pendulum.Pendulum)
# -----------------------------------------------------------------------------

def pendulum_to_dict(p: DateTime) -> Dict[str, Any]:
    """
    Converts a ``Pendulum`` or ``datetime`` object to a ``dict``.
    """
    return {
        'iso': str(p)
    }


# noinspection PyUnusedLocal
def dict_to_pendulum(d: Dict[str, Any],
                     pendulum_class: ClassType) -> DateTime:
    """
    Converts a ``dict`` object back to a ``Pendulum``.
    """
    return pendulum.parse(d['iso'])


register_class_for_json(
    cls=DateTime,
    obj_to_dict_fn=pendulum_to_dict,
    dict_to_obj_fn=dict_to_pendulum
)


# -----------------------------------------------------------------------------
# pendulum.Date
# -----------------------------------------------------------------------------

def pendulumdate_to_dict(p: Date) -> Dict[str, Any]:
    """
    Converts a ``pendulum.Date`` object to a ``dict``.
    """
    return {
        'iso': str(p)
    }


# noinspection PyUnusedLocal
def dict_to_pendulumdate(d: Dict[str, Any],
                         pendulumdate_class: ClassType) -> Date:
    """
    Converts a ``dict`` object back to a ``pendulum.Date``.
    """
    # noinspection PyTypeChecker
    return pendulum.parse(d['iso']).date()


register_class_for_json(
    cls=Date,
    obj_to_dict_fn=pendulumdate_to_dict,
    dict_to_obj_fn=dict_to_pendulumdate
)

# -----------------------------------------------------------------------------
# unused
# -----------------------------------------------------------------------------

# def timezone_to_initdict(x: Timezone) -> Dict[str, Any]:
#     kwargs = {
#         'name': x.name,
#         'transitions': x.transitions,
#         'tzinfos': x.tzinfos,
#         'default_tzinfo_index': x._default_tzinfo_index,  # NB different name
#         'utc_transition_times': x._utc_transition_times,  # NB different name
#     }
#     return kwargs_to_initdict(kwargs)


# def timezoneinfo_to_initdict(x: TimezoneInfo) -> Dict[str, Any]:
#     kwargs = {
#         'tz': x.tz,
#         'utc_offset': x.offset,  # NB different name
#         'is_dst': x.is_dst,
#         'dst': x.dst_,  # NB different name
#         'abbrev': x.abbrev,
#     }
#     return kwargs_to_initdict(kwargs)

# register_class_for_json(
#     cls=Transition,
#     obj_to_dict_fn=make_instance_to_initdict([
#         'unix_time', 'tzinfo_index', 'pre_time', 'time', 'pre_tzinfo_index'
#     ])
# )
# register_class_for_json(
#     cls=Timezone,
#     obj_to_dict_fn=timezone_to_initdict
# )
# register_class_for_json(
#     cls=TimezoneInfo,
#     obj_to_dict_fn=timezoneinfo_to_initdict
# )


# =============================================================================
# Testing
# =============================================================================

def simple_eq(one: Instance, two: Instance, attrs: List[str]) -> bool:
    """
    Test if two objects are equal, based on a comparison of the specified
    attributes ``attrs``.
    """
    return all(getattr(one, a) == getattr(two, a) for a in attrs)


def unit_tests():

    class BaseTestClass(object):
        def __repr__(self) -> str:
            return auto_repr(self, with_addr=True)

        def __str__(self) -> str:
            return repr(self)

    @register_for_json
    class SimpleThing(BaseTestClass):
        def __init__(self, a, b, c, d: datetime.datetime = None):
            self.a = a
            self.b = b
            self.c = c
            self.d = d or datetime.datetime.now()

        def __eq__(self, other: 'SimpleThing') -> bool:
            return simple_eq(self, other, ['a', 'b', 'c', 'd'])

    # If you comment out the decorator for this derived class, serialization
    # will fail, and that is a good thing (derived classes shouldn't be
    # serialized on a "have a try" basis).
    @register_for_json
    class DerivedThing(BaseTestClass):
        def __init__(self, a, b, c, d: datetime.datetime = None, e: int = 5,
                     f: datetime.date = None):
            self.a = a
            self.b = b
            self.c = c
            self.d = d or datetime.datetime.now()
            self.e = e
            self.f = f or datetime.date.today()

        def __eq__(self, other: 'SimpleThing') -> bool:
            return simple_eq(self, other, ['a', 'b', 'c', 'd', 'e'])

    @register_for_json(method=METHOD_STRIP_UNDERSCORE)
    class UnderscoreThing(BaseTestClass):
        def __init__(self, a, b, c):
            self._a = a
            self._b = b
            self._c = c

        # noinspection PyProtectedMember
        def __eq__(self, other: 'UnderscoreThing') -> bool:
            return simple_eq(self, other, ['_a', '_b', '_c'])

    @register_for_json(method=METHOD_PROVIDES_INIT_ARGS_KWARGS)
    class InitDictThing(BaseTestClass):
        def __init__(self, a, b, c):
            self.p = a
            self.q = b
            self.r = c

        def __eq__(self, other: 'InitDictThing') -> bool:
            return simple_eq(self, other, ['p', 'q', 'r'])

        def init_args_kwargs(self) -> ArgsKwargsTuple:
            args = []
            kwargs = {'a': self.p, 'b': self.q, 'c': self.r}
            return args, kwargs

    @register_for_json(method=METHOD_PROVIDES_INIT_KWARGS)
    class KwargsDictThing(BaseTestClass):
        def __init__(self, a, b, c):
            self.p = a
            self.q = b
            self.r = c

        def __eq__(self, other):
            return simple_eq(self, other, ['p', 'q', 'r'])

        def init_kwargs(self) -> KwargsDict:
            return {'a': self.p, 'b': self.q, 'c': self.r}

    def check_json(start: Any) -> None:
        print(repr(start))
        encoded = json_encode(start)
        print("-> JSON: " + repr(encoded))
        resurrected = json_decode(encoded)
        print("-> resurrected: " + repr(resurrected))
        assert resurrected == start
        print("... OK")
        print()

    check_json(SimpleThing(1, 2, 3))
    check_json(DerivedThing(1, 2, 3, e=6))
    check_json(UnderscoreThing(1, 2, 3))
    check_json(InitDictThing(1, 2, 3))
    check_json(KwargsDictThing(1, 2, 3))

    dump_map()

    print("\nAll OK.\n")


if __name__ == '__main__':
    unit_tests()
