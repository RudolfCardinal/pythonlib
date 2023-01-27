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

import unittest

from PyPDF2 import PdfWriter

from cardinal_pythonlib.pdf import PdfPlan


class PdfPlanTests(unittest.TestCase):
    def test_html_added_to_writer(self) -> None:
        html = """
<!DOCTYPE html>
<html lang="en">
    <head>
        <title>The Title</title>
        <meta charset="utf-8">
    </head>

    <body>
    Main text
    </body>

</html>
        """
        plan = PdfPlan(
            is_html=True,
            html=html,
        )

        writer = PdfWriter()
        self.assertEqual(len(writer.pages), 0)

        plan.add_to_writer(writer)
        self.assertEqual(len(writer.pages), 1)

        page = writer.pages[0]

        self.assertIn("Main text", page.extract_text())
