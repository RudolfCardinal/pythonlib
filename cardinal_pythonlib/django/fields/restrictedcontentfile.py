#!/usr/bin/env python
# cardinal_pythonlib/django/fields/restrictedcontentfile.py

"""
===============================================================================

    Original code copyright (C) 2009-2020 Rudolf Cardinal (rudolf@pobox.com).

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

**Django field class storing a file (by reference to a disk file, as for
"django.db.models.FileField") but also implementing limits on the maximum
upload size.**

"""

from typing import Any

# noinspection PyUnresolvedReferences
from django import forms
# noinspection PyUnresolvedReferences
from django.core.files.uploadedfile import UploadedFile
# noinspection PyUnresolvedReferences
from django.db import models
# noinspection PyUnresolvedReferences
from django.template.defaultfilters import filesizeformat
# noinspection PyUnresolvedReferences
from django.utils.translation import ugettext_lazy


# =============================================================================
# ContentTypeRestrictedFileField
# =============================================================================

class ContentTypeRestrictedFileField(models.FileField):
    """
    Same as ``FileField``, but you can specify:

    - ``content_types`` - list containing allowed content_types.
      Example: ``['application/pdf', 'image/jpeg']``
    - ``max_upload_size`` - a number indicating the maximum file size allowed
      for upload.

      .. code-block:: none

        2.5MB - 2621440
        5MB - 5242880
        10MB - 10485760
        20MB - 20971520
        50MB - 5242880
        100MB - 104857600
        250MB - 214958080
        500MB - 429916160

    See:

    - https://djangosnippets.org/snippets/2206/
    - https://docs.djangoproject.com/en/1.8/ref/files/uploads/
    - https://stackoverflow.com/questions/2472422/django-file-upload-size-limit
    """
    def __init__(self, *args, **kwargs) -> None:
        self.content_types = kwargs.pop("content_types", None)
        if self.content_types is None:
            self.content_types = []
        self.max_upload_size = kwargs.pop("max_upload_size", None)
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs) -> Any:
        data = super().clean(*args, **kwargs)
        # log.debug("data: {!r}", data)
        f = data.file
        if not isinstance(f, UploadedFile):  # RNC
            # no new file uploaded; there won't be a content-type to check
            return data
        # log.debug("f: {!r}", f)
        content_type = f.content_type
        if content_type not in self.content_types:
            raise forms.ValidationError(ugettext_lazy(
                'Filetype not supported.'))
        if hasattr(f, "size"):  # e.g. Django 2.1.2
            uploaded_file_size = f.size
        elif hasattr(f, "_size"):  # e.g. Django 1.8 ?
            # noinspection PyProtectedMember,PyUnresolvedReferences
            uploaded_file_size = f._size
        else:
            raise AssertionError(
                f"Don't know how to get file size from {f!r}")
        if (self.max_upload_size is not None and
                uploaded_file_size > self.max_upload_size):
            raise forms.ValidationError(ugettext_lazy(
                'Please keep filesize under %s. Current filesize %s')
                % (filesizeformat(self.max_upload_size),
                   filesizeformat(uploaded_file_size)))
        return data

