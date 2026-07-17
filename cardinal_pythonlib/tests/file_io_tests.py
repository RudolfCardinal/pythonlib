# cardinal_pythonlib/tests/file_io_tests.py

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

**Test support functions for file I/O**

"""

import subprocess
from tempfile import TemporaryDirectory
from unittest import mock, TestCase

from cardinal_pythonlib.file_io import remove_gzip_timestamp


class FileIoTests(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.mock_temp_directory = mock.Mock(spec=TemporaryDirectory)

        self.mock_newzip = mock.Mock()
        self.mock_open = mock.mock_open(mock=self.mock_newzip)
        self.mock_cm = mock.Mock(
            return_value=mock.Mock(
                __enter__=mock.Mock(return_value=self.mock_temp_directory),
                __exit__=mock.Mock(),
            )
        )

        self.mock_new_zip_filename = "full_path_of_zip_file"
        self.mock_join = mock.Mock(return_value=self.mock_new_zip_filename)

        self.mock_gunzip_popen = mock.Mock()
        self.mock_gzip_communicate = mock.Mock()
        self.mock_gzip_popen = mock.Mock(
            communicate=self.mock_gzip_communicate
        )

        self.mock_popen = mock.Mock(
            side_effect=[
                self.mock_gunzip_popen,
                self.mock_gzip_popen,
            ]
        )
        self.mock_copyfile = mock.Mock()

    def test_remove_gzip_timestamp_creates_new_file(self) -> None:
        # Assume gunzip, gzip and shutil.copyfile() are working as expected
        # so mock everything out and check the mocks are all called with the
        # right arguments.
        original_filename = "test_gzip_file.gz"

        with (
            mock.patch("cardinal_pythonlib.file_io.open", self.mock_open),
            mock.patch(
                "cardinal_pythonlib.file_io.tempfile.TemporaryDirectory",
                self.mock_cm,
            ),
            mock.patch(
                "cardinal_pythonlib.file_io.os.path.join", self.mock_join
            ),
            mock.patch(
                "cardinal_pythonlib.file_io.subprocess.Popen", self.mock_popen
            ),
            mock.patch(
                "cardinal_pythonlib.file_io.shutil.copyfile",
                self.mock_copyfile,
            ),
        ):
            remove_gzip_timestamp(original_filename)

        self.mock_join.assert_called_once_with(
            self.mock_temp_directory, original_filename
        )
        self.mock_open.assert_called_once_with(
            self.mock_new_zip_filename, "wb"
        )
        self.mock_popen.assert_has_calls(
            [
                mock.call(
                    ["gunzip", "-c", original_filename], stdout=subprocess.PIPE
                ),
                mock.call(
                    ["gzip", "-9", "-n"],
                    stdin=self.mock_gunzip_popen.stdout,
                    stdout=self.mock_newzip(),
                ),
            ]
        )
        self.mock_gzip_communicate.assert_called_once()
        self.mock_copyfile.assert_called_once_with(
            self.mock_new_zip_filename, original_filename
        )
