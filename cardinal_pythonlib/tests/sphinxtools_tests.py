#!/usr/bin/env python
# cardinal_pythonlib/tests/sphinxtools_tests.py

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

**Unit tests.**

"""

import os
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest import TestCase

from cardinal_pythonlib.sphinxtools import FileToAutodocument


class FileToAutodocumentTests(TestCase):
    def setUp(self) -> None:
        super().setUp()

    def test_pygments_language(self) -> None:
        with TemporaryDirectory() as test_dir:
            with NamedTemporaryFile(suffix=".py", dir=test_dir) as f:
                doc = FileToAutodocument(
                    source_filename=f.name,
                    project_root_dir=test_dir,
                    target_rst_filename="",
                )

        self.assertEqual(doc.pygments_language, "Python")

    def test_pygments_language_override_by_extension(self) -> None:
        overrides = {
            "*.pro": "none",
        }

        with TemporaryDirectory() as test_dir:
            with NamedTemporaryFile(suffix=".pro", dir=test_dir) as f:
                doc = FileToAutodocument(
                    source_filename=f.name,
                    project_root_dir=test_dir,
                    target_rst_filename="",
                    pygments_language_override=overrides,
                )

        self.assertEqual(doc.pygments_language, "none")

    def test_pygments_language_override_by_filename(self) -> None:
        with TemporaryDirectory() as test_dir:
            with NamedTemporaryFile(suffix=".cpp", dir=test_dir) as f:
                overrides = {
                    os.path.basename(f.name): "none",
                }

                doc = FileToAutodocument(
                    source_filename=f.name,
                    project_root_dir=test_dir,
                    target_rst_filename="",
                    pygments_language_override=overrides,
                )

        self.assertEqual(doc.pygments_language, "none")
