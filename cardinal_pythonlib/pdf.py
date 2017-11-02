#!/usr/bin/env python
# cardinal_pythonlib/pdf.py

"""
===============================================================================
    Copyright (C) 2009-2017 Rudolf Cardinal (rudolf@pobox.com).

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

Support functions to serve PDFs from CGI scripts.

"""

import io
import logging
import os
from pprint import pformat
import shutil
import sys
import tempfile
from typing import Any, Dict, Iterable, Union

from cardinal_pythonlib.logs import BraceStyleAdapter
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from semantic_version import Version

# =============================================================================
# Conditional/optional imports
# =============================================================================

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)

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


class Processors:
    XHTML2PDF = "xhtml2pdf"
    WEASYPRINT = "weasyprint"
    PDFKIT = "pdfkit"


_WKHTMLTOPDF_FILENAME = shutil.which("wkhtmltopdf")

if pdfkit:
    _DEFAULT_PROCESSOR = Processors.PDFKIT  # the best
elif weasyprint:
    _DEFAULT_PROCESSOR = Processors.WEASYPRINT  # imperfect tables
else:
    _DEFAULT_PROCESSOR = Processors.XHTML2PDF  # simple/slow


# =============================================================================
# PdfPlan
# =============================================================================

class PdfPlan(object):
    def __init__(self,
                 # HTML mode
                 is_html: bool = False,
                 html: str = None,
                 header_html: str = None,
                 footer_html: str = None,
                 wkhtmltopdf_filename: str = None,
                 wkhtmltopdf_options: Dict[str, Any] = None,
                 # Filename mode
                 is_filename: bool = False,
                 filename: str = None):
        assert is_html != is_filename, "Specify is_html XOR is_filename"
        self.is_html = is_html
        # is_html options:
        self.html = html
        self.header_html = header_html
        self.footer_html = footer_html
        self.wkhtmltopdf_filename = wkhtmltopdf_filename
        self.wkhtmltopdf_options = wkhtmltopdf_options

        self.is_filename = is_filename
        # is_filename options
        self.filename = filename

    def add_to_writer(self,
                      writer: PdfFileWriter,
                      start_recto: bool = True) -> None:
        if self.is_html:
            pdf = get_pdf_from_html(
                html=self.html,
                header_html=self.header_html,
                footer_html=self.footer_html,
                wkhtmltopdf_filename=self.wkhtmltopdf_filename,
                wkhtmltopdf_options=self.wkhtmltopdf_options)
            append_memory_pdf_to_writer(pdf, writer, start_recto=start_recto)
        elif self.is_filename:
            if start_recto and writer.getNumPages() % 2 != 0:
                writer.addBlankPage()
            writer.appendPagesFromReader(PdfFileReader(
                open(self.filename, 'rb')))
        else:
            raise AssertionError("PdfPlan: shouldn't get here!")


# =============================================================================
# Ancillary functions for PDFs
# =============================================================================

def assert_processor_available(processor: str) -> None:
    if processor not in [Processors.XHTML2PDF,
                         Processors.WEASYPRINT,
                         Processors.PDFKIT]:
        raise AssertionError("rnc_pdf.set_pdf_processor: invalid PDF processor"
                             " specified")
    if processor == Processors.WEASYPRINT and not weasyprint:
        raise RuntimeError("rnc_pdf: Weasyprint requested, but not available")
    if processor == Processors.XHTML2PDF and not xhtml2pdf:
        raise RuntimeError("rnc_pdf: xhtml2pdf requested, but not available")
    if processor == Processors.PDFKIT and not pdfkit:
        raise RuntimeError("rnc_pdf: pdfkit requested, but not available")


def get_default_fix_pdfkit_encoding_bug() -> bool:
    # Auto-determine.
    if pdfkit is None:
        return False
    else:
        return bool(Version(pdfkit.__version__) == Version("0.5.0"))


def get_pdf_from_html(html: str,
                      header_html: str = None,
                      footer_html: str = None,
                      wkhtmltopdf_filename: str = _WKHTMLTOPDF_FILENAME,
                      wkhtmltopdf_options: Dict[str, Any] = None,
                      file_encoding: str = "utf-8",
                      debug_options: bool = False,
                      debug_content: bool = False,
                      fix_pdfkit_encoding_bug: bool = None,
                      processor: str = _DEFAULT_PROCESSOR) -> bytes:
    """
    Takes HTML and returns a PDF.

    For preference, uses wkhtmltopdf (with pdfkit)
        - faster than xhtml2pdf
        - tables not buggy like Weasyprint
        - however, doesn't support CSS Paged Media, so we have the
          header_html and footer_html options to allow you to pass appropriate
          HTML content to serve as the header/footer (rather than passing it
          within the main HTML).
    """
    wkhtmltopdf_options = wkhtmltopdf_options or {}  # type: Dict[str, Any]
    assert_processor_available(processor)

    if debug_content:
        log.debug("html: {}", html)
        log.debug("header_html: {}", header_html)
        log.debug("footer_html: {}", footer_html)

    if fix_pdfkit_encoding_bug is None:
        fix_pdfkit_encoding_bug = get_default_fix_pdfkit_encoding_bug()

    if processor == Processors.XHTML2PDF:
        memfile = io.BytesIO()
        # noinspection PyUnresolvedReferences
        xhtml2pdf.document.pisaDocument(html, memfile)
        # ... returns a document, but we don't use it, so we don't store it to
        # stop pychecker complaining
        # http://xhtml2pdf.appspot.com/static/pisa-en.html
        memfile.seek(0)
        return memfile.read()
        # http://stackoverflow.com/questions/3310584

    elif processor == Processors.WEASYPRINT:
        # http://ampad.de/blog/generating-pdfs-django/
        return weasyprint.HTML(string=html).write_pdf()

    elif processor == Processors.PDFKIT:

        # Config:
        if not wkhtmltopdf_filename:
            config = None
        else:
            if fix_pdfkit_encoding_bug:  # needs to be True for pdfkit==0.5.0
                log.debug("Attempting to fix bug in pdfkit (e.g. version 0.5.0)"
                          " by encoding wkhtmltopdf_filename to UTF-8")
                config = pdfkit.configuration(
                    wkhtmltopdf=wkhtmltopdf_filename.encode('utf-8'))
                # the bug is that pdfkit.pdfkit.PDFKit.__init__ will attempt to
                # decode the string in its configuration object;
                # https://github.com/JazzCore/python-pdfkit/issues/32
            else:
                config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_filename)

        # Temporary files that a subprocess can read:
        #   http://stackoverflow.com/questions/15169101
        # wkhtmltopdf requires its HTML files to have ".html" extensions:
        #   http://stackoverflow.com/questions/5776125
        h_filename = None
        f_filename = None
        try:
            if header_html:
                h_fd, h_filename = tempfile.mkstemp(suffix='.html')
                os.write(h_fd, header_html.encode(file_encoding))
                os.close(h_fd)
                wkhtmltopdf_options["header-html"] = h_filename
            if footer_html:
                f_fd, f_filename = tempfile.mkstemp(suffix='.html')
                os.write(f_fd, footer_html.encode(file_encoding))
                os.close(f_fd)
                wkhtmltopdf_options["footer-html"] = f_filename
            if debug_options:
                log.debug("wkhtmltopdf config: {!r}", config)
                log.debug("wkhtmltopdf_options: {}",
                          pformat(wkhtmltopdf_options))
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


def pdf_from_html(html: str,
                  header_html: str = None,
                  footer_html: str = None,
                  wkhtmltopdf_filename: str = _WKHTMLTOPDF_FILENAME,
                  wkhtmltopdf_options: Dict[str, Any] = None,
                  file_encoding: str = "utf-8",
                  debug_options: bool = False,
                  debug_content: bool = False,
                  fix_pdfkit_encoding_bug: bool = True,
                  processor: str = _DEFAULT_PROCESSOR) -> bytes:
    """
    Older function name for get_pdf_from_html.
    """
    return get_pdf_from_html(html=html,
                             header_html=header_html,
                             footer_html=footer_html,
                             wkhtmltopdf_filename=wkhtmltopdf_filename,
                             wkhtmltopdf_options=wkhtmltopdf_options,
                             file_encoding=file_encoding,
                             debug_options=debug_options,
                             debug_content=debug_content,
                             fix_pdfkit_encoding_bug=fix_pdfkit_encoding_bug,
                             processor=processor)


def make_pdf_on_disk_from_html(
        html: str,
        output_path: str,
        header_html: str = None,
        footer_html: str = None,
        wkhtmltopdf_filename: str = _WKHTMLTOPDF_FILENAME,
        wkhtmltopdf_options: Dict[str, Any] = None,
        file_encoding: str = "utf-8",
        debug_options: bool = False,
        debug_content: bool = False,
        fix_pdfkit_encoding_bug: bool = None,
        processor: str = _DEFAULT_PROCESSOR) -> bool:
    """
    Takes HTML and writes a PDF to the file specified by output_path.
    """
    wkhtmltopdf_options = wkhtmltopdf_options or {}  # type: Dict[str, Any]

    if debug_content:
        log.debug("html: {}", html)
        log.debug("header_html: {}", header_html)
        log.debug("footer_html: {}", footer_html)

    if fix_pdfkit_encoding_bug is None:
        fix_pdfkit_encoding_bug = get_default_fix_pdfkit_encoding_bug()

    if processor == Processors.XHTML2PDF:
        with open(output_path, mode='wb') as outfile:
            # noinspection PyUnresolvedReferences
            xhtml2pdf.document.pisaDocument(html, outfile)
        return True

    elif processor == Processors.WEASYPRINT:
        return weasyprint.HTML(string=html).write_pdf(output_path)

    elif processor == Processors.PDFKIT:

        # Config:
        if not wkhtmltopdf_filename:
            config = None
        else:
            if fix_pdfkit_encoding_bug:  # needs to be True for pdfkit==0.5.0
                config = pdfkit.configuration(
                    wkhtmltopdf=wkhtmltopdf_filename.encode('utf-8'))
                # the bug is that pdfkit.pdfkit.PDFKit.__init__ will attempt to
                # decode the string in its configuration object;
                # https://github.com/JazzCore/python-pdfkit/issues/32
            else:
                config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_filename)

        # Temporary files that a subprocess can read:
        #   http://stackoverflow.com/questions/15169101
        # wkhtmltopdf requires its HTML files to have ".html" extensions:
        #   http://stackoverflow.com/questions/5776125
        h_filename = None
        f_filename = None
        try:
            if header_html:
                h_fd, h_filename = tempfile.mkstemp(suffix='.html')
                os.write(h_fd, header_html.encode(file_encoding))
                os.close(h_fd)
                wkhtmltopdf_options["header-html"] = h_filename
            if footer_html:
                f_fd, f_filename = tempfile.mkstemp(suffix='.html')
                os.write(f_fd, footer_html.encode(file_encoding))
                os.close(f_fd)
                wkhtmltopdf_options["footer-html"] = f_filename
            if debug_options:
                log.debug("wkhtmltopdf config: {!r}", config)
                log.debug("wkhtmltopdf_options: {!r}", wkhtmltopdf_options)
            kit = pdfkit.pdfkit.PDFKit(html, 'string', configuration=config,
                                       options=wkhtmltopdf_options)
            return kit.to_pdf(path=output_path)
        finally:
            if h_filename:
                os.remove(h_filename)
            if f_filename:
                os.remove(f_filename)

    else:
        raise AssertionError("Unknown PDF engine")


def pdf_from_writer(writer: Union[PdfFileWriter, PdfFileMerger]) -> bytes:
    """
    Extracts a PDF (as binary data) from a PyPDF2 writer or merger object.
    """
    memfile = io.BytesIO()
    writer.write(memfile)
    memfile.seek(0)
    return memfile.read()


def serve_pdf_to_stdout(pdf: bytes) -> None:
    """
    Serves a PDF to stdout (for web servers).

    Writes a "Content-Type: application/pdf" header and then the PDF to stdout.
    """
    # http://stackoverflow.com/questions/312230/proper-mime-type-for-pdf-files
    # http://www.askapache.com/htaccess/pdf-cookies-headers-rewrites.html
    # http://stackoverflow.com/questions/2374427
    # print("Content-type: text/plain\n")  # for debugging
    print("Content-Type: application/pdf\n")
    sys.stdout.write(pdf)


def make_pdf_writer() -> PdfFileWriter:
    """
    Creates a PyPDF2 writer.
    """
    return PdfFileWriter()


def append_memory_pdf_to_writer(input_pdf: bytes,
                                writer: PdfFileWriter,
                                start_recto: bool = True) -> None:
    """
    Appends a PDF (as bytes in memory) to a PyPDF2 writer.
    """
    if not input_pdf:
        return
    if start_recto and writer.getNumPages() % 2 != 0:
        writer.addBlankPage()
        # ... suitable for double-sided printing
    infile = io.BytesIO(input_pdf)
    reader = PdfFileReader(infile)
    for page_num in range(reader.numPages):
        writer.addPage(reader.getPage(page_num))


def append_pdf(input_pdf: bytes, output_writer: PdfFileWriter):
    """
    Appends a PDF to a pyPDF writer. Legacy interface.
    """
    append_memory_pdf_to_writer(input_pdf=input_pdf,
                                writer=output_writer)


# =============================================================================
# Serve concatenated PDFs
# =============================================================================
# Two ways in principle to do this:
# (1) Load data from each PDF into memory; concatenate; serve the result.
# (2) With each PDF on disk, create a temporary file (e.g. with pdftk),
#     serve the result (e.g. in one go), then delete the temporary file.
#     This may be more memory-efficient.
#     However, there can be problems:
#       http://stackoverflow.com/questions/7543452/how-to-launch-a-pdftk-subprocess-while-in-wsgi  # noqa
# Others' examples:
#   https://gist.github.com/zyegfryed/918403
#   https://gist.github.com/grantmcconnaughey/ce90a689050c07c61c96
#   http://stackoverflow.com/questions/3582414/removing-tmp-file-after-return-httpresponse-in-django  # noqa

# def append_disk_pdf_to_writer(filename, writer):
#     """Appends a PDF from disk to a pyPDF writer."""
#     if writer.getNumPages() % 2 != 0:
#         writer.addBlankPage()
#         # ... keeps final result suitable for double-sided printing
#     with open(filename, mode='rb') as infile:
#         reader = PdfFileReader(infile)
#         for page_num in range(reader.numPages):
#             writer.addPage(reader.getPage(page_num))


def get_concatenated_pdf_from_disk(filenames: Iterable[str],
                                   start_recto: bool = True) -> bytes:
    """
    Concatenates PDFs from disk and returns them as an in-memory binary PDF.
    """
    # http://stackoverflow.com/questions/17104926/pypdf-merging-multiple-pdf-files-into-one-pdf  # noqa
    # https://en.wikipedia.org/wiki/Recto_and_verso
    if start_recto:
        writer = PdfFileWriter()
        for filename in filenames:
            if filename:
                if writer.getNumPages() % 2 != 0:
                    writer.addBlankPage()
                writer.appendPagesFromReader(
                    PdfFileReader(open(filename, 'rb')))
        return pdf_from_writer(writer)
    else:
        merger = PdfFileMerger()
        for filename in filenames:
            if filename:
                merger.append(open(filename, 'rb'))
        return pdf_from_writer(merger)


def get_concatenated_pdf_in_memory(
        pdf_plans: Iterable[PdfPlan],
        start_recto: bool = True) -> bytes:
    """
    Concatenates PDFs and returns them as an in-memory binary PDF.
    """
    writer = PdfFileWriter()
    for pdfplan in pdf_plans:
        pdfplan.add_to_writer(writer, start_recto=start_recto)
    return pdf_from_writer(writer)


# =============================================================================
# Main -- to enable logging for imports, for debugging
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig()
    log.setLevel(logging.DEBUG)
