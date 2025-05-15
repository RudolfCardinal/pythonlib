# cardinal_pythonlib/tests/extract_text_tests.py

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

from email import message_from_string, policy
from email.message import EmailMessage
from io import BytesIO
import os
import subprocess
from tempfile import mkdtemp, NamedTemporaryFile
from unittest import mock, TestCase

from faker import Faker
from faker_file.providers.docx_file import DocxFileProvider
from faker_file.providers.eml_file import EmlFileProvider
from faker_file.providers.helpers.inner import (
    create_inner_docx_file,
    create_inner_eml_file,
)
from faker_file.providers.odt_file import OdtFileProvider
from faker_file.providers.txt_file import TxtFileProvider
from faker_file.providers.xml_file import XmlFileProvider

from cardinal_pythonlib.extract_text import (
    convert_msg_to_text,
    document_to_text,
    TextProcessingConfig,
    update_external_tools,
)


class ExtractTextTestCase(TestCase):
    def setUp(self) -> None:
        self.config = TextProcessingConfig()
        self.fake = Faker("en-US")  # en-US to avoid Lorem Ipsum from en-GB
        self.fake.seed_instance(12345)


class DocumentToTextTests(ExtractTextTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.empty_dir = mkdtemp()

        self._replace_external_tools_with_fakes()
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
        self.fake.add_provider(DocxFileProvider)
        self.fake.add_provider(EmlFileProvider)
        self.fake.add_provider(OdtFileProvider)
        self.fake.add_provider(TxtFileProvider)
        self.fake.add_provider(XmlFileProvider)

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

    def test_raises_when_filename_empty(self) -> None:
        with self.assertRaises(ValueError) as cm:
            document_to_text(filename="")

        self.assertIn("no filename and no blob", str(cm.exception))

    def test_raises_when_filename_and_blob(self) -> None:
        with self.assertRaises(ValueError) as cm:
            document_to_text(filename="foo", blob=b"bar")

        self.assertIn("specify either filename or blob", str(cm.exception))

    def test_raises_when_blob_but_no_extension(self) -> None:
        with self.assertRaises(ValueError) as cm:
            document_to_text(blob=b"bar")

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

    def test_doc_will_be_converted_with_antiword(self) -> None:
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

    def test_dot_will_be_converted_with_antiword(self) -> None:
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
        text = document_to_text(
            filename=docx.data["filename"], config=self.config
        )

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

    def test_empty_htm_converted(self) -> None:
        text = document_to_text(
            blob="".encode("utf-8"), extension="htm", config=self.config
        )
        self.assertEqual(text, "")

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
        text = document_to_text(
            filename=odt.data["filename"], config=self.config
        )

        self.assertEqual(text.strip(), content)

    def test_pdf_will_be_converted_with_pdftotext(self) -> None:
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

    def test_rtf_will_be_converted_with_unrtf(self) -> None:
        with mock.patch(
            "cardinal_pythonlib.extract_text.UNRTF_SUPPORTS_QUIET", True
        ):
            with mock.patch.multiple(
                "cardinal_pythonlib.extract_text.subprocess",
                Popen=self.mock_popen,
            ):
                with NamedTemporaryFile(
                    suffix=".rtf", delete=False
                ) as temp_file:
                    temp_file.close()
                    document_to_text(
                        filename=temp_file.name, config=self.config
                    )

        expected_calls = [
            mock.call(
                (
                    f"{self.empty_dir}/unrtf",
                    "--text",
                    "--nopict",
                    "--quiet",
                    temp_file.name,
                ),
                stdout=subprocess.PIPE,
            ),
        ]
        self.mock_popen.assert_has_calls(expected_calls)

    def test_txt_converted(self) -> None:
        content = self.fake.paragraph(nb_sentences=10)
        txt_file = self.fake.txt_file(content=content)
        text = document_to_text(filename=txt_file.data["filename"])

        self.assertEqual(text.strip(), content)

    def test_xml_converted(self) -> None:
        name = self.fake.name()
        address = self.fake.address()

        xml_file = self.fake.xml_file(
            num_rows=1,
            data_columns={
                "name": name,
                "address": address,
            },
        )
        text = document_to_text(filename=xml_file.data["filename"])

        self.assertEqual(text.strip(), f"{name}{address}")

    def test_eml_converted(self) -> None:
        content = self.fake.paragraph(nb_sentences=10)
        eml_file = self.fake.eml_file(content=content)
        text = document_to_text(filename=eml_file.data["filename"])

        self.assertEqual(text.strip(), content)

    def test_eml_with_docx_attachment_converted(self) -> None:
        body_content = self.fake.paragraph(nb_sentences=10)
        docx_content = self.fake.paragraph(nb_sentences=10)

        docx_file_args = dict(content=docx_content)
        options = dict(
            count=1,
            create_inner_file_func=create_inner_docx_file,
            create_inner_file_args=docx_file_args,
        )

        eml_file = self.fake.eml_file(
            content=body_content,
            options=options,
        )
        self.config.width = 0
        text = document_to_text(
            filename=eml_file.data["filename"], config=self.config
        )

        self.assertIn(body_content, text)
        self.assertIn(docx_content, text)

    def test_eml_with_nested_docx_attachment_converted(self) -> None:
        outer_email_content = self.fake.paragraph(nb_sentences=10)
        inner_email_content = self.fake.paragraph(nb_sentences=10)

        docx_content = self.fake.paragraph(nb_sentences=10)

        docx_file_args = dict(content=docx_content)
        docx_options = dict(
            count=1,
            create_inner_file_func=create_inner_docx_file,
            create_inner_file_args=docx_file_args,
        )
        eml_file_args = dict(
            content=inner_email_content,
            options=docx_options,
        )
        eml_options = dict(
            count=1,
            create_inner_file_func=create_inner_eml_file,
            create_inner_file_args=eml_file_args,
        )

        eml_file = self.fake.eml_file(
            content=outer_email_content,
            options=eml_options,
        )

        self.config.width = 0
        text = document_to_text(
            filename=eml_file.data["filename"], config=self.config
        )

        self.assertIn(outer_email_content, text)
        self.assertIn(inner_email_content, text)
        self.assertIn(docx_content, text)

    def test_eml_html_body_preferred_over_text(self) -> None:
        # Contrived example. Normally these would have the same content
        text_content = self.fake.paragraph(nb_sentences=10)
        html_content = self.fake.paragraph(nb_sentences=10)
        html = f"""
<!DOCTYPE html>
<html>
<head>
</head>
<body>
{html_content}
</body>
</html>
"""
        # faker-file can't do this yet
        message = EmailMessage()
        message.set_content(text_content)
        message.add_alternative(html, subtype="html")
        blob = message.as_bytes()

        text = document_to_text(
            blob=blob, extension=".eml", config=self.config
        )

        self.assertIn(html_content, text)
        self.assertNotIn(text_content, text)

    def test_eml_latin1_html_decoded_correctly(self) -> None:
        content = """From: foo@example.org
To: bar@example.org
Subject: Latin-1 test
Content-Type: multipart/mixed; boundary="==="
MIME-Version: 1.0

--===
Content-Type: text/html; charset="iso-8859-1"
Content-Transfer-Encoding: quoted-printable

<html><head>
<meta http-equiv=3D"Content-Type" content=3D"text/html; charset=3Diso-8859-=
1">
</head>
<body lang=3D"EN-GB">
Caf=E9
</body>
</html>
--===--
"""

        message = message_from_string(content, policy=policy.default)
        blob = message.as_bytes()

        text = document_to_text(
            blob=blob, extension=".eml", config=self.config
        )

        self.assertIn("Café", text)

    def test_eml_with_no_charset_converted(self) -> None:
        text_content = self.fake.paragraph(nb_sentences=10)

        content = f"""From: bar@example.org
Subject: No charset
To: foo@example.org
Mime-Version: 1.0
Content-Type: multipart/mixed;boundary="==="

--===
Content-Type: text/plain

{text_content}

--===--

"""

        message = message_from_string(content, policy=policy.default)
        blob = message.as_bytes()

        text = document_to_text(
            blob=blob, extension=".eml", config=self.config
        )

        self.assertIn(text_content, text)

    def test_eml_with_no_content_type_converted(self) -> None:
        text_content = self.fake.paragraph(nb_sentences=10)

        content = f"""From: bar@example.org
Subject: No content type
To: foo@example.org
Mime-Version: 1.0
Content-Type: multipart/mixed;boundary="==="

--===

{text_content}

--===--

"""

        message = message_from_string(content, policy=policy.default)
        blob = message.as_bytes()

        text = document_to_text(
            blob=blob, extension=".eml", config=self.config
        )

        self.assertIn(text_content, text)

    def test_eml_with_empty_body_converted(self) -> None:
        content = """From: bar@example.org
Subject: No body
To: foo@example.org
Mime-Version: 1.0
Content-Type: multipart/mixed;boundary="==="

--===
--===--
"""
        message = message_from_string(content, policy=policy.default)
        blob = message.as_bytes()

        text = document_to_text(
            blob=blob, extension=".eml", config=self.config
        )

        self.assertEqual("", text)

    def test_eml_with_illegal_multibyte_sequence_replaced(self) -> None:
        content = """From: bar@example.org
Subject: Illegal multibyte sequence
To: foo@example.org
Mime-Version: 1.0
Content-Type: multipart/mixed;boundary="==="

--===
Content-Type: text/html; charset="big5"
Content-Transfer-Encoding: quoted-printable

<html><head>
<meta http-equiv=3D"Content-Type" content=3D"text/html; charset=3Dbig5">
</head>
<body>
=F9=F9
</body>
</html>
--===--
"""
        message = message_from_string(content, policy=policy.default)
        blob = message.as_bytes()

        text = document_to_text(
            blob=blob, extension=".eml", config=self.config
        )

        self.assertEqual(text.strip(), "??")

    def test_eml_invalid_surrogate_characters_replaced(self) -> None:
        content = """From: bar@example.org
Subject: Invalid surrogate characters
To: foo@example.org
Mime-Version: 1.0
Content-Type: multipart/mixed;boundary="==="

--===
Content-Type: text/html; charset="windows-1252"
Content-Transfer-Encoding: quoted-printable

<html><head>
<meta http-equiv=3D"Content-Type" content=3D"text/html; charset=3DWindows-1=
252">
</head>
<body>
&#55357;&#56898;
</body>
</html>
--===--
"""
        message = message_from_string(content, policy=policy.default)
        blob = message.as_bytes()

        text = document_to_text(
            blob=blob, extension=".eml", config=self.config
        )

        self.assertEqual(text.strip(), "??")

    def test_unsupported_will_be_converted_with_strings(self) -> None:
        with mock.patch.multiple(
            "cardinal_pythonlib.extract_text.subprocess",
            Popen=self.mock_popen,
        ):
            with NamedTemporaryFile(suffix=".exe", delete=False) as temp_file:
                temp_file.close()
                document_to_text(filename=temp_file.name, config=self.config)

        expected_calls = [
            mock.call(
                (
                    f"{self.empty_dir}/strings",
                    temp_file.name,
                ),
                stdout=subprocess.PIPE,
            ),
        ]
        self.mock_popen.assert_has_calls(expected_calls)


class ConvertMsgToTextTests(ExtractTextTestCase):
    # There is no easy way to create test Outlook msg files and we don't want
    # to store real ones so we mock the interface to extract-msg and assume the
    # library itself is working correctly.
    def setUp(self) -> None:
        super().setUp()
        self.dummy_filename = "dummy_filename.msg"
        self.dummy_blob = b"dummy blob"

    def test_raises_when_no_filename_or_blob(self) -> None:
        with self.assertRaises(ValueError) as cm:
            convert_msg_to_text()

        self.assertIn("no filename and no blob", str(cm.exception))

    def test_raises_when_filename_and_blob(self) -> None:
        with self.assertRaises(ValueError) as cm:
            convert_msg_to_text(filename="foo", blob=b"bar")

        self.assertIn("specify either filename or blob", str(cm.exception))

    def test_blob_passed_to_openmsg(self) -> None:
        content = self.fake.paragraph(nb_sentences=10)

        mock_msgfile = mock.Mock(body=content, htmlBody=None, attachments=[])
        mock_openmsg = mock.Mock(return_value=mock_msgfile)
        with mock.patch.multiple(
            "cardinal_pythonlib.extract_text",
            openMsg=mock_openmsg,
        ):
            convert_msg_to_text(blob=self.dummy_blob, config=self.config)

        expected_calls = [mock.call(self.dummy_blob, delayAttachments=False)]
        mock_openmsg.assert_has_calls(expected_calls)

    def test_file_passed_to_openmsg(self) -> None:
        content = self.fake.paragraph(nb_sentences=10)

        mock_msgfile = mock.Mock(body=content, htmlBody=None, attachments=[])
        mock_openmsg = mock.Mock(return_value=mock_msgfile)
        with mock.patch.multiple(
            "cardinal_pythonlib.extract_text",
            openMsg=mock_openmsg,
        ):
            convert_msg_to_text(
                filename=self.dummy_filename, config=self.config
            )

        expected_calls = [
            mock.call(self.dummy_filename, delayAttachments=False)
        ]
        mock_openmsg.assert_has_calls(expected_calls)

    def test_text_body_converted(self) -> None:
        content = self.fake.paragraph(nb_sentences=10)

        mock_msgfile = mock.Mock(body=content, htmlBody=None, attachments=[])
        mock_openmsg = mock.Mock(return_value=mock_msgfile)
        with mock.patch.multiple(
            "cardinal_pythonlib.extract_text",
            openMsg=mock_openmsg,
        ):
            converted = convert_msg_to_text(
                filename=self.dummy_filename, config=self.config
            )

        self.assertEqual(converted, content)

    def test_html_body_converted(self) -> None:
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

        mock_msgfile = mock.Mock(
            body=None, htmlBody=html.encode("utf-8"), attachments=[]
        )
        mock_openmsg = mock.Mock(return_value=mock_msgfile)
        with mock.patch.multiple(
            "cardinal_pythonlib.extract_text",
            openMsg=mock_openmsg,
        ):
            converted = convert_msg_to_text(
                filename=self.dummy_filename, config=self.config
            )

        self.assertEqual(converted.strip(), content)

    def test_attachment_converted(self) -> None:
        self.fake.add_provider(DocxFileProvider)

        dummy_filename = "dummy_filename.msg"

        content = self.fake.paragraph(nb_sentences=10)
        docx = self.fake.docx_file(content=content, raw=True)
        mock_attachment = mock.Mock(
            # null termination seen in the real world
            # https://github.com/TeamMsgExtractor/msg-extractor/issues/464
            extension=".docx\x00",
            data=BytesIO(docx).read(),
        )
        mock_msgfile = mock.Mock(
            body=None, htmlBody=None, attachments=[mock_attachment]
        )
        mock_openmsg = mock.Mock(return_value=mock_msgfile)
        with mock.patch.multiple(
            "cardinal_pythonlib.extract_text",
            openMsg=mock_openmsg,
        ):
            self.config.width = 0
            converted = convert_msg_to_text(dummy_filename, config=self.config)

        self.assertEqual(converted.strip(), content)
