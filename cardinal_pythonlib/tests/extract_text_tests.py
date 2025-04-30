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
import subprocess
from tempfile import mkdtemp, NamedTemporaryFile
from unittest import mock, TestCase

from faker import Faker
from faker_file.providers.docx_file import DocxFileProvider
from faker_file.providers.odt_file import OdtFileProvider
from faker_file.providers.pdf_file import PdfFileProvider

from cardinal_pythonlib.extract_text import (
    document_to_text,
    TextProcessingConfig,
    update_external_tools,
)


class DocumentToTextTests(TestCase):
    def setUp(self) -> None:
        self.empty_dir = mkdtemp()

        self._replace_external_tools_with_fakes()
        self.config = TextProcessingConfig()
        self._create_mock_objects()
        self._register_faker_providers()

    def _create_mock_objects(self) -> None:
        # Some mock empty output that we don't check
        mock_decode = mock.Mock(return_value="")
        mock_stdout = mock.Mock(decode=mock_decode)
        mock_communicate = mock.Mock(return_value=(mock_stdout, None))
        self.mock_popen = mock.Mock(
            return_value=mock.Mock(communicate=mock_communicate)
        )

    def _register_faker_providers(self) -> None:
        self.fake = Faker()
        self.fake.add_provider(DocxFileProvider)
        self.fake.add_provider(OdtFileProvider)
        self.fake.add_provider(PdfFileProvider)

    def _replace_external_tools_with_fakes(self) -> None:
        # For external tools we assume the tools are running correctly
        # and we just check that they are invoked with the correct arguments.

        tool_names = [
            "antiword",
            "pdftotext",
            "strings",
            "strings2",
            "unrtf",
        ]

        tools_dir = {t: os.path.join(self.empty_dir, t) for t in tool_names}
        update_external_tools(tools_dir)

    def tearDown(self) -> None:
        os.rmdir(self.empty_dir)

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
            filename = os.path.join(self.empty_dir, "foo")
            document_to_text(filename=filename)

        self.assertIn("no such file", str(cm.exception))

    def test_csv_converted(self) -> None:
        content = "one,two,three"

        with NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
            temp_file.write(content.encode("utf-8"))
            temp_file.close()
            text = document_to_text(filename=temp_file.name)

        self.assertEqual(text, content)

    def test_doc_converted_with_antiword(self) -> None:
        with mock.patch.multiple(
            "cardinal_pythonlib.extract_text.subprocess",
            Popen=self.mock_popen,
        ):
            with NamedTemporaryFile(suffix=".doc", delete=False) as temp_file:
                temp_file.close()
                document_to_text(filename=temp_file.name, config=self.config)

        expected_calls = [
            mock.call(
                (
                    f"{self.empty_dir}/antiword",
                    "-w",
                    str(self.config.width),
                    temp_file.name,
                ),
                stdout=subprocess.PIPE,
            ),
        ]
        self.mock_popen.assert_has_calls(expected_calls)

    def test_dot_converted_with_antiword(self) -> None:
        with mock.patch.multiple(
            "cardinal_pythonlib.extract_text.subprocess",
            Popen=self.mock_popen,
        ):
            with NamedTemporaryFile(suffix=".dot", delete=False) as temp_file:
                temp_file.close()
                document_to_text(filename=temp_file.name)

        expected_calls = [
            mock.call(
                (
                    f"{self.empty_dir}/antiword",
                    "-w",
                    str(self.config.width),
                    temp_file.name,
                ),
                stdout=subprocess.PIPE,
            ),
        ]
        self.mock_popen.assert_has_calls(expected_calls)

    def test_docx_converted(self) -> None:
        content = self.fake.paragraph(nb_sentences=10)

        docx = self.fake.docx_file(content=content)
        self.config.width = 0
        text = document_to_text(docx.data["filename"], config=self.config)

        self.assertEqual(text.strip(), content)

    def test_htm_converted(self) -> None:
        content = self.fake.paragraph(nb_sentences=10)

        html = f"""
<!DOCTYPE html>
<html>
<head>
</head>
<body>
{content}
</body>
</html>
"""

        text = document_to_text(
            blob=html.encode("utf-8"), extension="htm", config=self.config
        )
        self.assertEqual(text.strip(), content)

    def test_log_converted(self) -> None:
        content = """
2025-04-02 06:05:43,772 INFO Starting unattended upgrades script
2025-04-02 06:05:43,772 INFO Allowed origins are: o=Ubuntu,a=focal, o=Ubuntu,a=focal-security, o=UbuntuESMApps,a=focal-apps-security, o=UbuntuESM,a=focal-infra-security
"""  # noqa: E501

        text = document_to_text(
            blob=content.encode("utf-8"), extension="log", config=self.config
        )

        self.assertEqual(text.strip(), content.strip())

    def test_odt_converted(self) -> None:
        content = self.fake.paragraph(nb_sentences=10)

        odt = self.fake.odt_file(content=content)
        self.config.width = 0
        text = document_to_text(odt.data["filename"], config=self.config)

        self.assertEqual(text.strip(), content)

    def test_pdf_converted(self) -> None:
        with mock.patch.multiple(
            "cardinal_pythonlib.extract_text.subprocess",
            Popen=self.mock_popen,
        ):
            with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.close()
                document_to_text(filename=temp_file.name, config=self.config)

        expected_calls = [
            mock.call(
                (
                    f"{self.empty_dir}/pdftotext",
                    temp_file.name,
                    "-",
                ),
                stdout=subprocess.PIPE,
            ),
        ]
        self.mock_popen.assert_has_calls(expected_calls)
