#!/usr/bin/env python
# cardinal_pythonlib/modules.py

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

**Functions to work with Python modules.**

"""

import importlib
from importlib.machinery import ExtensionFileLoader, EXTENSION_SUFFIXES
import inspect
import logging
import os
import os.path
import pkgutil
# noinspection PyUnresolvedReferences
from types import ModuleType
from typing import Dict, List, Union

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Module management
# =============================================================================

def import_submodules(package: Union[str, ModuleType],
                      base_package_for_relative_import: str = None,
                      recursive: bool = True) -> Dict[str, ModuleType]:
    """
    Import all submodules of a module, recursively, including subpackages.

    Args:
        package: package (name or actual module)
        base_package_for_relative_import: path to prepend?
        recursive: import submodules too?

    Returns:
        dict: mapping from full module name to module

    """
    # http://stackoverflow.com/questions/3365740/how-to-import-all-submodules
    if isinstance(package, str):
        package = importlib.import_module(package,
                                          base_package_for_relative_import)
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


# =============================================================================
# For package developers
# =============================================================================

def is_builtin_module(module: ModuleType) -> bool:
    """
    Is this module a built-in module, like ``os``?
    Method is as per :func:`inspect.getfile`.
    """
    assert inspect.ismodule(module)
    return not hasattr(module, "__file__")


def is_module_a_package(module: ModuleType) -> bool:
    assert inspect.ismodule(module)
    return os.path.basename(inspect.getfile(module)) == "__init__.py"


def is_c_extension(module: ModuleType) -> bool:
    """
    Modified from
    https://stackoverflow.com/questions/20339053/in-python-how-can-one-tell-if-a-module-comes-from-a-c-extension.
    
    ``True`` only if the passed module is a C extension implemented as a
    dynamically linked shared library specific to the current platform.

    Args:
        module: Previously imported module object to be tested.

    Returns:
        bool: ``True`` only if this module is a C extension.
        
    Examples:
        
    .. code-block:: python
    
        from cardinal_pythonlib.modules import is_c_extension
        
        import os
        import _elementtree as et
        import numpy
        import numpy.core.multiarray as numpy_multiarray
        
        is_c_extension(os)  # False
        is_c_extension(numpy)  # False
        is_c_extension(et)  # False on my system (Python 3.5.6). True in the original example.
        is_c_extension(numpy_multiarray)  # True

    """  # noqa
    assert inspect.ismodule(module), '"{}" not a module.'.format(module)

    # If this module was loaded by a PEP 302-compliant CPython-specific loader
    # loading only C extensions, this module is a C extension.
    if isinstance(getattr(module, '__loader__', None), ExtensionFileLoader):
        return True

    # If it's built-in, it's not a C extension.
    if is_builtin_module(module):
        return False

    # Else, fallback to filetype matching heuristics.
    #
    # Absolute path of the file defining this module.
    module_filename = inspect.getfile(module)

    # "."-prefixed filetype of this path if any or the empty string otherwise.
    module_filetype = os.path.splitext(module_filename)[1]

    # This module is only a C extension if this path's filetype is that of a
    # C extension specific to the current platform.
    return module_filetype in EXTENSION_SUFFIXES


def contains_c_extension(module: ModuleType,
                         import_all_submodules: bool = True,
                         include_external_imports: bool = False,
                         seen: List[ModuleType] = None) -> bool:
    """
    Extends :func:`is_c_extension` by asking: is this module, or any of its
    submodules, a C extension?

    Args:
        module: Previously imported module object to be tested.
        import_all_submodules: explicitly import all submodules of this module?
        include_external_imports: check modules in other packages that this
            module imports?
        seen: used internally for recursion (to deal with recursive modules);
            should be ``None`` when called by users

    Returns:
        bool: ``True`` only if this module or one of its submodules is a C
        extension.

    Examples:

    .. code-block:: python

        import logging
        from cardinal_pythonlib.modules import contains_c_extension
        from cardinal_pythonlib.logs import main_only_quicksetup_rootlogger
        
        import _elementtree as et
        import os
        
        import arrow
        import alembic
        import django
        import numpy
        import numpy.core.multiarray as numpy_multiarray
        
        log = logging.getLogger(__name__)
        # logging.basicConfig(level=logging.DEBUG)  # be verbose
        main_only_quicksetup_rootlogger(level=logging.DEBUG)
        
        contains_c_extension(os)  # False
        contains_c_extension(et)  # False
        
        contains_c_extension(numpy)  # True -- different from is_c_extension()
        contains_c_extension(numpy_multiarray)  # True
        
        contains_c_extension(arrow)  # False
        
        contains_c_extension(alembic)  # False
        contains_c_extension(alembic, include_external_imports=True)  # True
        # ... this example shows that Alembic imports hashlib, which can import
        #     _hashlib, which is a C extension; however, that doesn't stop us (for
        #     example) installing Alembic on a machine with no C compiler
        
        contains_c_extension(django)

    """  # noqa
    assert inspect.ismodule(module), '"{}" not a module.'.format(module)

    if seen is None:  # only true for the top-level call
        seen = []  # type: List[ModuleType]
    if module in seen:  # modules can "contain" themselves
        # already inspected; avoid infinite loops
        return False
    seen.append(module)

    # Check the thing we were asked about
    is_c_ext = is_c_extension(module)
    log.info("Is module {!r} a C extension? {}".format(module, is_c_ext))
    if is_c_ext:
        return True
    if is_builtin_module(module):
        # built-in, therefore we stop searching it
        return False

    # Now check any children, in a couple of ways

    top_level_module = seen[0]
    top_path = os.path.dirname(top_level_module.__file__)

    # Recurse using dir(). This picks up modules that are automatically
    # imported by our top-level model. But it won't pick up all submodules;
    # try e.g. for django.
    for candidate_name in dir(module):
        candidate = getattr(module, candidate_name)
        try:
            if not inspect.ismodule(candidate):
                # not a module
                continue
        except Exception:
            # e.g. a Django module that won't import until we configure its
            # settings
            log.error("Failed to test ismodule() status of {!r}".format(
                candidate))
            continue
        if is_builtin_module(candidate):
            # built-in, therefore we stop searching it
            continue

        candidate_fname = getattr(candidate, "__file__")
        if not include_external_imports:
            if os.path.commonpath([top_path, candidate_fname]) != top_path:
                log.debug("Skipping, not within the top-level module's "
                          "directory: {!r}".format(candidate))
                continue
        # Recurse:
        if contains_c_extension(
                module=candidate,
                import_all_submodules=False,  # only done at the top level, below  # noqa
                include_external_imports=include_external_imports,
                seen=seen):
            return True

    if import_all_submodules:
        if not is_module_a_package(module):
            log.debug("Top-level module is not a package: {!r}".format(module))
            return False

        # Otherwise, for things like Django, we need to recurse in a different
        # way to scan everything.
        # See https://stackoverflow.com/questions/3365740/how-to-import-all-submodules.  # noqa
        log.debug("Walking path: {!r}".format(top_path))
        try:
            for loader, module_name, is_pkg in pkgutil.walk_packages([top_path]):  # noqa
                if not is_pkg:
                    log.debug("Skipping, not a package: {!r}".format(
                        module_name))
                    continue
                log.debug("Manually importing: {!r}".format(module_name))
                try:
                    candidate = loader.find_module(module_name)\
                        .load_module(module_name)  # noqa
                except Exception:
                    # e.g. Alembic "autogenerate" gives: "ValueError: attempted
                    # relative import beyond top-level package"; or Django
                    # "django.core.exceptions.ImproperlyConfigured"
                    log.error("Package failed to import: {!r}".format(
                        module_name))
                    continue
                if contains_c_extension(
                        module=candidate,
                        import_all_submodules=False,  # only done at the top level  # noqa
                        include_external_imports=include_external_imports,
                        seen=seen):
                    return True
        except Exception:
            log.error("Unable to walk packages further; no C extensions "
                      "detected so far!")
            raise

    return False
