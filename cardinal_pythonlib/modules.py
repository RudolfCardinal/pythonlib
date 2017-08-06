#!/usr/bin/env python
# cardinal_pythonlib/modules.py

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

import importlib
import logging
import pkgutil
# noinspection PyUnresolvedReferences
from types import ModuleType
from typing import Dict, Union

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Module management
# =============================================================================

def import_submodules(package: Union[str, ModuleType],
                      base_package_for_relative_import: str = None,
                      recursive: bool = True) -> Dict[str, ModuleType]:
    # http://stackoverflow.com/questions/3365740/how-to-import-all-submodules
    """ Import all submodules of a module, recursively, including subpackages

    :param package: package (name or actual module)
    :param base_package_for_relative_import: path to prepend?
    :param recursive: import submodules too
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
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


