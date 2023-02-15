#!/usr/bin/env python
# cardinal_pythonlib/tests/pdf_tests.py

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
"""

import io
import os
import tempfile
import unittest

import pdfkit
from pypdf import PdfReader, PdfWriter

from cardinal_pythonlib.pdf import (
    get_concatenated_pdf_from_disk,
    get_concatenated_pdf_in_memory,
    make_pdf_writer,
    PdfPlan,
)


# noinspection DuplicatedCode
class PdfPlanTests(unittest.TestCase):
    def test_html_added_to_writer(self) -> None:
        html = create_html("Main text")

        plan = PdfPlan(is_html=True, html=html)

        writer = PdfWriter()
        self.assertEqual(len(writer.pages), 0)

        plan.add_to_writer(writer)
        self.assertEqual(len(writer.pages), 1)

        words = writer.pages[0].extract_text().split()
        self.assertIn("Main", words)
        self.assertIn("text", words)

    def test_html_added_to_writer_with_blank_page(self) -> None:
        html = create_html("Main text")

        plan = PdfPlan(is_html=True, html=html)

        writer = PdfWriter()
        # Not the blank page we're testing. We just want the page count to be
        # odd.
        writer.add_blank_page(width=100, height=100)
        self.assertEqual(len(writer.pages), 1)

        plan.add_to_writer(writer, start_recto=True)
        self.assertEqual(len(writer.pages), 3)

        self.assertEqual(writer.pages[0].extract_text(), "")
        self.assertEqual(writer.pages[1].extract_text(), "")

        words = writer.pages[2].extract_text().split()
        self.assertIn("Main", words)
        self.assertIn("text", words)

    def test_file_added_to_writer(self) -> None:
        filename = create_pdf_file("Main text")
        plan = PdfPlan(is_filename=True, filename=filename)

        writer = PdfWriter()
        self.assertEqual(len(writer.pages), 0)

        plan.add_to_writer(writer)
        self.assertEqual(len(writer.pages), 1)

        words = writer.pages[0].extract_text().split()
        self.assertIn("Main", words)
        self.assertIn("text", words)

        os.remove(filename)

    def test_file_added_to_writer_with_blank_page(self) -> None:
        filename = create_pdf_file("Main text")
        plan = PdfPlan(is_filename=True, filename=filename)

        writer = PdfWriter()
        # Not the blank page we're testing. We just want the page count to be
        # odd.
        writer.add_blank_page(width=100, height=100)
        self.assertEqual(len(writer.pages), 1)

        plan.add_to_writer(writer, start_recto=True)
        self.assertEqual(len(writer.pages), 3)

        self.assertEqual(writer.pages[0].extract_text(), "")
        self.assertEqual(writer.pages[1].extract_text(), "")
        words = writer.pages[2].extract_text().split()
        self.assertIn("Main", words)
        self.assertIn("text", words)

        os.remove(filename)


# noinspection DuplicatedCode
class FunctionTests(unittest.TestCase):
    def test_concatenated_pdf_from_disk_inserts_blank_pages(self) -> None:
        filenames = [
            create_pdf_file("One"),
            create_pdf_file("Two"),
            create_pdf_file("Three"),
        ]

        pdf_data = get_concatenated_pdf_from_disk(filenames)
        reader = PdfReader(io.BytesIO(pdf_data))

        self.assertEqual(len(reader.pages), 5)
        self.assertEqual(reader.pages[0].extract_text(), "One")
        self.assertEqual(reader.pages[1].extract_text(), "")
        self.assertEqual(reader.pages[2].extract_text(), "Two")
        self.assertEqual(reader.pages[3].extract_text(), "")
        self.assertEqual(reader.pages[4].extract_text(), "Three")

    def test_concatenated_pdf_from_disk_merges_files(self) -> None:
        filenames = [
            create_pdf_file("One"),
            create_pdf_file("Two"),
            create_pdf_file("Three"),
        ]

        pdf_data = get_concatenated_pdf_from_disk(filenames, start_recto=False)
        reader = PdfReader(io.BytesIO(pdf_data))

        self.assertEqual(len(reader.pages), 3)
        self.assertEqual(reader.pages[0].extract_text(), "One")
        self.assertEqual(reader.pages[1].extract_text(), "Two")
        self.assertEqual(reader.pages[2].extract_text(), "Three")

    def test_concatenated_pdf_in_memory_inserts_blank_pages(self) -> None:
        plans = [
            PdfPlan(is_html=True, html=create_html("One")),
            PdfPlan(is_html=True, html=create_html("Two")),
            PdfPlan(is_html=True, html=create_html("Three")),
        ]

        pdf_data = get_concatenated_pdf_in_memory(plans)
        reader = PdfReader(io.BytesIO(pdf_data))

        self.assertEqual(len(reader.pages), 5)
        self.assertEqual(reader.pages[0].extract_text(), "One")
        self.assertEqual(reader.pages[1].extract_text(), "")
        self.assertEqual(reader.pages[2].extract_text(), "Two")
        self.assertEqual(reader.pages[3].extract_text(), "")
        self.assertEqual(reader.pages[4].extract_text(), "Three")

    def test_concatenated_pdf_in_memory_merges_plans(self) -> None:
        plans = [
            PdfPlan(is_html=True, html=create_html("One")),
            PdfPlan(is_html=True, html=create_html("Two")),
            PdfPlan(is_html=True, html=create_html("Three")),
        ]

        pdf_data = get_concatenated_pdf_in_memory(plans, start_recto=False)
        reader = PdfReader(io.BytesIO(pdf_data))

        self.assertEqual(len(reader.pages), 3)
        self.assertEqual(reader.pages[0].extract_text(), "One")
        self.assertEqual(reader.pages[1].extract_text(), "Two")
        self.assertEqual(reader.pages[2].extract_text(), "Three")

    def test_make_pdf_writer(self) -> None:
        writer = make_pdf_writer()
        self.assertIsInstance(writer, PdfWriter)


def create_pdf_file(text: str) -> str:
    pdf_data = pdfkit.from_string(text)

    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".pdf", delete=False
    ) as pdf_file:
        pdf_file.write(pdf_data)
        filename = pdf_file.name

    return filename


def create_html(text: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
    <head>
        <title>The Title</title>
        <meta charset="utf-8">
    </head>

    <body>
    {text}
    </body>

</html>
        """
