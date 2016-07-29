#!/usr/bin/env python
# -*- encoding: utf8 -*-

"""Support functions to serve PDFs from CGI scripts.

Author: Rudolf Cardinal (rudolf@pobox.com)
Created: October 2012
Last update: 27 Jan 2016

Copyright/licensing:

    Copyright (C) 2012-2015 Rudolf Cardinal (rudolf@pobox.com).

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

from __future__ import division, print_function, absolute_import
import io
import logging
import os
import sys
import tempfile
from typing import Any, Dict, Union

# noinspection PyPackageRequirements
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter

# =============================================================================
# Conditional/optional imports
# =============================================================================

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

pdfkit = None
xhtml2pdf = None
weasyprint = None

# Preference 1
try:
    log.debug("trying pdfkit...")
    # noinspection PyPackageRequirements
    import pdfkit  # sudo apt-get install wkhtmltopdf; sudo pip install pdfkit
    log.debug("pdfkit: loaded")
except ImportError:
    pdfkit = None
    log.debug("pdfkit: failed to load")

if pdfkit:
    log.debug("pdfkit found, so skipping other PDF rendering engines")
else:
    try:
        # noinspection PyPackageRequirements
        import xhtml2pdf  # pip install xhtml2pdf
        # noinspection PyPackageRequirements
        import xhtml2pdf.document  # pip install xhtml2pdf
        log.debug("xhtml2pdf: loaded")
    except ImportError:
        xhtml2pdf = None
        log.debug("xhtml2pdf: failed to load")

    try:
        log.debug("trying weasyprint...")
        # noinspection PyPackageRequirements
        import weasyprint
        log.debug("weasyprint: loaded")
    except ImportError:
        weasyprint = None
        log.debug("weasyprint: failed to load")

# =============================================================================
# Onwards
# =============================================================================

if not any([xhtml2pdf, weasyprint, pdfkit]):
    raise RuntimeError("No PDF engine (xhtml2pdf, weasyprint, pdfkit) "
                       "available; can't load")

XHTML2PDF = "xhtml2pdf"
WEASYPRINT = "weasyprint"
PDFKIT = "pdfkit"
_wkhtmltopdf_filename = None

if pdfkit:
    processor = PDFKIT  # the best
elif weasyprint:
    processor = WEASYPRINT  # imperfect tables
else:
    processor = XHTML2PDF  # simple/slow

if sys.version_info > (3,):
    # noinspection PyShadowingBuiltins
    buffer = memoryview


# =============================================================================
# Ancillary functions for PDFs
# =============================================================================

def set_processor(new_processor: str = WEASYPRINT,
                  wkhtmltopdf_filename: str = None) -> None:
    """Set the PDF processor."""
    global processor
    if new_processor not in [XHTML2PDF, WEASYPRINT, PDFKIT]:
        raise AssertionError("rnc_pdf.set_pdf_processor: invalid PDF processor"
                             " specified")
    if new_processor == WEASYPRINT and not weasyprint:
        raise RuntimeError("rnc_pdf: Weasyprint requested, but not available")
    if new_processor == XHTML2PDF and not xhtml2pdf:
        raise RuntimeError("rnc_pdf: xhtml2pdf requested, but not available")
    if new_processor == PDFKIT and not pdfkit:
        raise RuntimeError("rnc_pdf: pdfkit requested, but not available")
    global processor
    processor = new_processor
    global _wkhtmltopdf_filename
    _wkhtmltopdf_filename = wkhtmltopdf_filename
    log.info("PDF processor set to: " + processor)


def pdf_from_html(html: str,
                  header_html: str = None,
                  footer_html: str = None,
                  wkhtmltopdf_options: Dict[str, Any] = None,
                  file_encoding: str = "utf-8") -> bytes:  # TODO: check type
    """
    Takes HTML and returns a PDF (as a buffer in Python 2, or a memoryview
    in Python 3).
    For engines not supporting CSS Paged Media - meaning, here, wkhtmltopdf -
    the header_html and footer_html options allow you to pass appropriate HTML
    content to serve as the header/footer (rather than passing it within the
    main HTML).
    """
    if processor == XHTML2PDF:
        memfile = io.BytesIO()
        # noinspection PyUnresolvedReferences
        xhtml2pdf.document.pisaDocument(html, memfile)
        # ... returns a document, but we don't use it, so we don't store it to
        # stop pychecker complaining
        # http://xhtml2pdf.appspot.com/static/pisa-en.html
        memfile.seek(0)
        return buffer(memfile.read())
        # http://stackoverflow.com/questions/3310584

    elif processor == WEASYPRINT:
        # http://ampad.de/blog/generating-pdfs-django/
        return weasyprint.HTML(string=html).write_pdf()

    elif processor == PDFKIT:
        if _wkhtmltopdf_filename is None:
            config = None
        else:
            # config = pdfkit.configuration(wkhtmltopdf=_wkhtmltopdf_filename)
            # Curiously, while pdfkit.configuration just copies the
            # wkhtmltopdf parameter to self.wkhtmltopdf, the next stage, in
            # pdfkit.pdfkit.PDFKit.__init__, uses
            # self.wkhtmltopdf = \
            #       self.configuration.wkhtmltopdf.decode('utf-8'),
            # which then fails with
            # AttributeError: 'str' object has no attribute 'decode'.
            # So, it seems, we must pre-encode it...
            config = pdfkit.configuration(
                wkhtmltopdf=_wkhtmltopdf_filename.encode('utf-8'))
        # Temporary files that a subprocess can read:
        #   http://stackoverflow.com/questions/15169101
        # wkhtmltopdf requires its HTML files to have ".html" extensions:
        #   http://stackoverflow.com/questions/5776125
        h_filename = None
        f_filename = None
        try:
            if header_html:
                if not wkhtmltopdf_options:
                    wkhtmltopdf_options = {}
                h_fd, h_filename = tempfile.mkstemp(suffix='.html')
                os.write(h_fd, header_html.encode(file_encoding))
                os.close(h_fd)
                wkhtmltopdf_options["header-html"] = h_filename
            if footer_html:
                if not wkhtmltopdf_options:
                    wkhtmltopdf_options = {}
                f_fd, f_filename = tempfile.mkstemp(suffix='.html')
                os.write(f_fd, footer_html.encode(file_encoding))
                os.close(f_fd)
                wkhtmltopdf_options["footer-html"] = f_filename
            kit = pdfkit.pdfkit.PDFKit(html, 'string', configuration=config,
                                       options=wkhtmltopdf_options)
            return kit.to_pdf(path=None)
            # With "path=None", the to_pdf() function directly returns stdout
            # from a subprocess.Popen().communicate() call (see pdfkit.py).
            # Since universal_newlines is not set, stdout will be bytes in
            # Python 3.
        finally:
            if h_filename:
                os.remove(h_filename)
            if f_filename:
                os.remove(f_filename)

    else:
        raise AssertionError("Unknown PDF engine")


def pdf_from_writer(writer: Union[PdfFileWriter, PdfFileMerger]) -> bytes:
    """Extracts a PDF (as a buffer) from a PyPDF2 writer."""
    memfile = io.BytesIO()
    writer.write(memfile)
    memfile.seek(0)
    return buffer(memfile.read())


def serve_pdf_to_stdout(pdf: bytes) -> None:
    """Serves a PDF to stdout.

    Writes a "Content-Type: application/pdf" header and then the PDF to stdout.
    """
    # http://stackoverflow.com/questions/312230/proper-mime-type-for-pdf-files
    # http://www.askapache.com/htaccess/pdf-cookies-headers-rewrites.html
    # http://stackoverflow.com/questions/2374427
    # print("Content-type: text/plain\n")  # for debugging
    print("Content-Type: application/pdf\n")
    sys.stdout.write(pdf)


def make_pdf_writer() -> PdfFileWriter:
    """Creates a PyPDF2 writer."""
    return PdfFileWriter()


def append_pdf(input_pdf: bytes, output_writer: PdfFileWriter):
    """Appends a PDF to a pyPDF writer."""
    if input_pdf is None:
        return
    if output_writer.getNumPages() % 2 != 0:
        output_writer.addBlankPage()
        # ... suitable for double-sided printing
    infile = io.BytesIO(input_pdf)
    reader = PdfFileReader(infile)
    [
        output_writer.addPage(reader.getPage(page_num))
        for page_num in range(reader.numPages)
    ]


# =============================================================================
# Main -- to enable logging for imports, for debugging
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig()
    log.setLevel(logging.DEBUG)
