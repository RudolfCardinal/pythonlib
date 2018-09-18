#!/usr/bin/env python
# cardinal_pythonlib/django/fields/restrictedcontentfile.py

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

**Django field class storing a file (by reference to a disk file, as for
"django.db.models.FileField") but also implementing limits on the maximum
upload size.**

"""

from typing import Any

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy


# =============================================================================
# ContentTypeRestrictedFileField
# =============================================================================
# https://djangosnippets.org/snippets/2206/
# https://docs.djangoproject.com/en/1.8/ref/files/uploads/

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
    """
    def __init__(self, *args, **kwargs) -> None:
        self.content_types = kwargs.pop("content_types", None)
        if self.content_types is None:
            self.content_types = []
        self.max_upload_size = kwargs.pop("max_upload_size", None)
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs) -> Any:
        data = super().clean(*args, **kwargs)
        # log.debug("data: {}".format(repr(data)))
        f = data.file
        if not isinstance(f, UploadedFile):  # RNC
            # no new file uploaded; there won't be a content-type to check
            return data
        # log.debug("f: {}".format(repr(f)))
        content_type = f.content_type
        if content_type not in self.content_types:
            raise forms.ValidationError(ugettext_lazy(
                'Filetype not supported.'))
        # noinspection PyProtectedMember,PyUnresolvedReferences
        if self.max_upload_size is not None and f._size > self.max_upload_size:
            # noinspection PyProtectedMember,PyUnresolvedReferences
            raise forms.ValidationError(ugettext_lazy(
                'Please keep filesize under %s. Current filesize %s')
                % (filesizeformat(self.max_upload_size),
                   filesizeformat(f._size)))
        return data

