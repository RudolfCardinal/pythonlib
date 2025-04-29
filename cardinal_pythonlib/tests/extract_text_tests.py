# cardinal_pythonlib/tests/datetimefunc_tests.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Text extraction tests.**

"""

import os
from tempfile import TemporaryDirectory
from unittest import TestCase

from cardinal_pythonlib.extract_text import document_to_text


class DocumentToTextTests(TestCase):
    def test_raises_when_no_filename_or_blob(self) -> None:
        with self.assertRaises(ValueError) as cm:
            document_to_text()

        self.assertIn("no filename and no blob", str(cm.exception))

    def test_raises_when_filename_and_blob(self) -> None:
        with self.assertRaises(ValueError) as cm:
            document_to_text(filename="foo", blob="bar")

        self.assertIn("specify either filename or blob", str(cm.exception))

    def test_raises_when_blob_but_no_extension(self) -> None:
        with self.assertRaises(ValueError) as cm:
            document_to_text(blob="bar")

        self.assertIn("need extension hint for blob", str(cm.exception))

    def test_raises_when_not_a_file(self) -> None:
        with self.assertRaises(ValueError) as cm:
            with TemporaryDirectory() as temp_dir_name:
                filename = os.path.join(temp_dir_name, "foo")
                document_to_text(filename=filename)

        self.assertIn("no such file", str(cm.exception))
