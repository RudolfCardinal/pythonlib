#!/usr/bin/env python
# cardinal_pythonlib/plot.py

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

**Support for plotting via matplotlib.pyplot.**
"""

import io
# noinspection PyUnresolvedReferences
from types import ModuleType
from typing import TYPE_CHECKING, Union

from cardinal_pythonlib import rnc_web

if TYPE_CHECKING:
    try:
        # noinspection PyPackageRequirements
        from matplotlib.figure import Figure
    except ImportError:
        Figure = None


# =============================================================================
# Image embedding in PDFs
# =============================================================================
# xhtml2pdf (2013-04-11) supports PNG, but not SVG.
# You can convert SVG to PNG for embedding:
# http://stackoverflow.com/questions/787287
# You could make a PDF and append it, though that would (without further
# effort) lack the patient headers.

def png_img_html_from_pyplot_figure(fig: "Figure",
                                    dpi: int = 100,
                                    extra_html_class: str = None) -> str:
    """
    Converts a ``pyplot`` figure to an HTML IMG tag with encapsulated PNG.
    """
    if fig is None:
        return ""
    # Make a file-like object
    memfile = io.BytesIO()
    # In general, can do
    #   fig.savefig(filename/file-like-object/backend, format=...)
    # or
    #   backend.savefig(fig):
    # see e.g. http://matplotlib.org/api/backend_pdf_api.html
    fig.savefig(memfile, format="png", dpi=dpi)
    memfile.seek(0)
    pngblob = memoryview(memfile.read())
    return rnc_web.get_png_img_html(pngblob, extra_html_class)


def svg_html_from_pyplot_figure(fig: "Figure") -> str:
    """
    Converts a ``pyplot`` figure to an SVG tag.
    """
    if fig is None:
        return ""
    memfile = io.BytesIO()  # StringIO doesn't like mixing str/unicode
    fig.savefig(memfile, format="svg")
    return memfile.getvalue().decode("utf-8")  # returns a text/Unicode type
    # SVG works directly in HTML; it returns <svg ...></svg>


# =============================================================================
# Plotting
# =============================================================================

def set_matplotlib_fontsize(matplotlib: ModuleType,
                            fontsize: Union[int, float] = 12) -> None:
    """
    Sets the current font size within the ``matplotlib`` library.

    **WARNING:** not an appropriate method for multithreaded environments, as
    it writes (indirectly) to ``matplotlib`` global objects. See CamCOPS for
    alternative methods.
    """
    font = {
        # http://stackoverflow.com/questions/3899980
        # http://matplotlib.org/users/customizing.html
        'family': 'sans-serif',
        # ... serif, sans-serif, cursive, fantasy, monospace
        'style': 'normal',  # normal (roman), italic, oblique
        'variant': 'normal',  # normal, small-caps
        'weight': 'normal',
        # ... normal [=400], bold [=700], bolder [relative to current],
        # lighter [relative], 100, 200, 300, ..., 900
        'size': fontsize  # in pt (default 12)
    }
    matplotlib.rc('font', **font)
    legend = {
        # http://stackoverflow.com/questions/7125009
        'fontsize': fontsize
    }
    matplotlib.rc('legend', **legend)
