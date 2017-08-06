#!/usr/bin/env python
# cardinal_pythonlib/django/forms.py

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

from typing import List

from django import forms

from cardinal_pythonlib.nhs import is_valid_nhs_number


# =============================================================================
# Multiple values from a text area
# =============================================================================

def clean_int(x) -> int:
    try:
        return int(x)
    except ValueError:
        raise forms.ValidationError(
            "Cannot convert to integer: {}".format(repr(x)))


def clean_nhs_number(x) -> int:
    try:
        x = int(x)
        if not is_valid_nhs_number(x):
            raise ValueError
        return x
    except ValueError:
        raise forms.ValidationError(
            "Not a valid NHS number: {}".format(repr(x)))


class MultipleIntAreaField(forms.Field):
    # See also http://stackoverflow.com/questions/29303902/django-form-with-list-of-integers  # noqa
    widget = forms.Textarea

    def clean(self, value) -> List[int]:
        return [clean_int(x) for x in value.split()]


class MultipleNhsNumberAreaField(forms.Field):
    widget = forms.Textarea

    def clean(self, value) -> List[int]:
        return [clean_nhs_number(x) for x in value.split()]


class MultipleWordAreaField(forms.Field):
    widget = forms.Textarea

    def clean(self, value) -> List[str]:
        return value.split()


class SingleNhsNumberField(forms.IntegerField):
    def clean(self, value) -> int:
        return clean_nhs_number(value)
