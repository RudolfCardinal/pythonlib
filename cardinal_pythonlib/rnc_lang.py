#!/usr/bin/python
# -*- encoding: utf8 -*-

"""Support functions to do with the core language.

Author: Rudolf Cardinal (rudolf@pobox.com)
Created: 2013
Last update: 24 Sep 2015

Copyright/licensing:

    Copyright (C) 2013-2015 Rudolf Cardinal (rudolf@pobox.com).

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

import importlib
import logging
import pkgutil
import six
# noinspection PyUnresolvedReferences
from six.moves import range

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
# log.setLevel(logging.DEBUG)


# =============================================================================
# enum
# =============================================================================

def enum(**enums):
    """Enum support, as at http://stackoverflow.com/questions/36932"""
    return type('Enum', (), enums)


# =============================================================================
# AttrDict
# =============================================================================

class AttrDict(dict):
    # http://stackoverflow.com/questions/4984647
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


# =============================================================================
# Other dictionary operations
# =============================================================================

def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    # http://stackoverflow.com/questions/38987
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


# =============================================================================
# Helper functions
# =============================================================================

def convert_to_bool(x, default=None):
    if isinstance(x, bool):
        return x
    if not x:  # None, zero, blank string...
        return default
    try:
        return int(x) != 0
    except (TypeError, ValueError):
        pass
    try:
        return float(x) != 0
    except (TypeError, ValueError):
        pass
    if not isinstance(x, six.string_types):
        raise Exception("Unknown thing being converted to bool: {}".format(x))
    x = x.upper()
    if x in ["Y", "YES", "T", "TRUE"]:
        return True
    if x in ["N", "NO", "F", "FALSE"]:
        return False
    raise Exception("Unknown thing being converted to bool: {}".format(x))


def convert_attrs_to_bool(obj, attrs, default=None):
    for a in attrs:
        setattr(obj, a, convert_to_bool(getattr(obj, a), default=default))


def convert_attrs_to_uppercase(obj, attrs):
    for a in attrs:
        value = getattr(obj, a)
        if value is None:
            continue
        setattr(obj, a, value.upper())


def convert_attrs_to_lowercase(obj, attrs):
    for a in attrs:
        value = getattr(obj, a)
        if value is None:
            continue
        setattr(obj, a, value.lower())


def convert_to_int(x, default=None):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def convert_attrs_to_int(obj, attrs, default=None):
    for a in attrs:
        value = convert_to_int(getattr(obj, a), default=default)
        setattr(obj, a, value)


def raise_if_attr_blank(obj, attrs):
    for a in attrs:
        value = getattr(obj, a)
        if value is None or value is "":
            raise Exception("Blank attribute: {}".format(a))


def count_bool(blist):
    return sum([1 if x else 0 for x in blist])


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]


def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


# =============================================================================
# Module management
# =============================================================================

def import_submodules(package, recursive=True):
    # http://stackoverflow.com/questions/3365740/how-to-import-all-submodules
    """ Import all submodules of a module, recursively, including subpackages

    :param package: package (name or actual module)
    :param recursive: import submodules too
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        log.debug("importing: {}".format(full_name))
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results

# Note slightly nastier way: e.g.
#   # Task imports: everything in "tasks" directory
#   task_modules = glob.glob(os.path.dirname(__file__) + "/tasks/*.py")
#   task_modules = [os.path.basename(f)[:-3] for f in task_modules]
#   for tm in task_modules:
#       __import__(tm, locals(), globals())
