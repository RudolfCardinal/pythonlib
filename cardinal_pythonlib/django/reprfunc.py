#!/usr/bin/env python
# cardinal_pythonlib/django/reprfunc.py

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

from django.core.exceptions import ObjectDoesNotExist


def modelrepr(instance) -> str:
    """Default repr version of a Django model object, for debugging."""
    elements = []
    # noinspection PyProtectedMember
    for fieldname in [f.name for f in instance._meta.get_fields()]:
        try:
            value = repr(getattr(instance, fieldname))
        except ObjectDoesNotExist:
            value = "<RelatedObjectDoesNotExist>"
        elements.append("{}={}".format(fieldname, value))
    return "<{} <{}>>".format(type(instance).__name__,
                              ", ".join(elements))
    # - type(instance).__name__ gives the Python class name from an instance
    # - ... as does ModelClass.__name__ but we don't have that directly here
    # - instance._meta.model_name gives a lower-case version
