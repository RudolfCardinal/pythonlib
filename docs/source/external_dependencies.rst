..  crate_anon/docs/source/external_dependencies.rst

..  Copyright (C) 2009-2020 Rudolf Cardinal (rudolf@pobox.com).
    .
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
    .
        https://www.apache.org/licenses/LICENSE-2.0
    .
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.


External libraries
------------------

This package also installs (and uses or extends) the following packages, which
are generally "pure Python", meaning that they can easily be installed e.g. on
a Windows computer with no C compiler system installed.

- ``alembic``: http://alembic.zzzcomputing.com/
- ``appdirs``: https://pypi.org/project/appdirs/
- ``arrow``: https://arrow.readthedocs.io/
- ``beautifulsoup4``: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- ``chardet``: https://chardet.readthedocs.io/en/latest/
- ``colorlog``: https://pypi.org/project/colorlog/
- ``isodate``: https://pypi.org/project/isodate/
- ``numpy``: http://www.numpy.org/
- ``openpyxl``: https://openpyxl.readthedocs.io/
- ``pandas``: https://pandas.pydata.org/
- ``pdfminer.six``: https://pdfminersix.readthedocs.io/en/latest/
- ``pendulum``: https://pendulum.eustace.io/
- ``prettytable``: https://pypi.org/project/PrettyTable/
- ``psutil``: https://pypi.org/project/psutil/
- ``pygments``: https://pygments.org/
- ``pyparsing``: http://infohost.nmt.edu/tcc/help/pubs/pyparsing/web/index.html
- ``PyPDF2``: https://pythonhosted.org/PyPDF2/
- ``python-dateutil``: https://dateutil.readthedocs.io/en/stable/
- ``scipy``: https://www.scipy.org/
- ``semantic_version``: https://pypi.org/project/semantic_version/
- ``SQLAlchemy``: https://www.sqlalchemy.org/
- ``sqlparse``: https://sqlparse.readthedocs.io/
- ``xlrd``: https://pypi.org/project/xlrd/

The following packages will be used, if present, and an exception raised if you
use library code that requires one of these packages without it being
installed. They include large packages (e.g. Django), some other "less core"
aspects, and packages that require a C compiler and so may be harder to install
in some contexts.

- ``bcrypt``: https://pypi.org/project/bcrypt/ (C-based)
- ``colander``: https://docs.pylonsproject.org/projects/colander/
- ``cryptography``: https://cryptography.io/
- ``deform``: https://docs.pylonsproject.org/projects/deform/
- ``Django`` >= 4.2: https://www.djangoproject.com/
- ``dogpile.cache``: https://dogpilecache.readthedocs.io/
- ``libChEBIpy``: https://pypi.org/project/libChEBIpy/ (Python 2 only?)
- ``pyramid``: https://trypyramid.com/
- ``webob``: https://webob.org/ (used and installed by Pyramid)

The following packages will be used sometimes, but the library code won't
complain much if they are absent. They include some other C-based packages, one
that is specific to Windows and won't install on other platforms, and a
selection of PDF-handling libraries where there is not a clear best choice.

- ``brotlipy``: https://pypi.org/project/brotlipy/ (C-based)
- ``mmh3``: https://pypi.org/project/mmh3/ (C-based)
- ``matplotlib``: https://matplotlib.org/
- ``pdfkit``: https://pypi.org/project/pdfkit/
- ``pypiwin32``: https://pypi.org/project/pypiwin32/ (Windows only)
- ``weasyprint``: https://weasyprint.org/
- ``xhtml2pdf``: https://xhtml2pdf.readthedocs.io/

To *build* the library distribution (most people won't need this!), a few other
development libraries are required:

- ``sphinx``: https://www.sphinx-doc.org/
- ``sphinx_rtd_theme``: https://github.com/readthedocs/sphinx_rtd_theme
- ``twine``: https://pypi.org/project/twine/
