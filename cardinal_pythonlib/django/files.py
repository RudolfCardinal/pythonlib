#!/usr/bin/env python
# cardinal_pythonlib/django/files.py

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

import os
from typing import Any, Iterable

from django.db import models


# =============================================================================
# Making FileFields own their files (i.e. delete them afterwards)
# =============================================================================

# http://stackoverflow.com/questions/16041232/django-delete-filefield
# These two auto-delete files from filesystem when they are unneeded:
# ... with a bit of modification to make them generic (RNC)
# Attach them with signals; see e.g. Study model.
def auto_delete_files_on_instance_delete(instance: Any,
                                         fieldnames: Iterable[str]) -> None:
    """Deletes files from filesystem when object is deleted."""
    for fieldname in fieldnames:
        filefield = getattr(instance, fieldname, None)
        if filefield:
            if os.path.isfile(filefield.path):
                os.remove(filefield.path)


def auto_delete_files_on_instance_change(instance: Any,
                                         fieldnames: Iterable[str],
                                         model: models.Model) -> None:
    """Deletes files from filesystem when object is changed."""
    if not instance.pk:
        return  # instance not yet saved in database
    try:
        old_instance = model.objects.get(pk=instance.pk)
    except model.DoesNotExist:
        return  # old version gone from database entirely
    for fieldname in fieldnames:
        old_filefield = getattr(old_instance, fieldname, None)
        if not old_filefield:
            continue
        new_filefield = getattr(instance, fieldname, None)
        if old_filefield != new_filefield:
            if os.path.isfile(old_filefield.path):
                os.remove(old_filefield.path)
