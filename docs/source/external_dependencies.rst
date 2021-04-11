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


This package also installs (and uses or extends):

- ``alembic``: http://alembic.zzzcomputing.com/
- ``appdirs``: https://pypi.org/project/appdirs/
- ``beautifulsoup4``: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- ``colorlog``: https://pypi.org/project/colorlog/
- ``isodate``: https://pypi.org/project/isodate/
- ``numpy``: http://www.numpy.org/
- ``openpyxl``: https://openpyxl.readthedocs.io/
- ``pandas``: https://pandas.pydata.org/
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

The following will be used, if present (and an exception raised if you use
library code that requires one of these packages without it being installed):

- ``arrow``: https://arrow.readthedocs.io/
- ``bcrypt``: https://pypi.org/project/bcrypt/
- ``colander``: https://docs.pylonsproject.org/projects/colander/
- ``deform``: https://docs.pylonsproject.org/projects/deform/
- ``Django``: https://www.djangoproject.com/
- ``dogpile.cache``: https://dogpilecache.readthedocs.io/
- ``pyramid``: https://trypyramid.com/
- ``webob``: https://webob.org/ (used by Pyramid)

The following will be used, but the library code won't complain if not:

- ``mmh3``: https://pypi.org/project/mmh3/
- ``pdfkit``: https://pypi.org/project/pdfkit/
- ``pdfminer``: https://pypi.org/project/pdfminer/
- ``pypiwin32``: https://pypi.org/project/pypiwin32/
- ``pyth``: https://pyth.readthedocs.io/
- ``python-docx`` (``import docx``): https://python-docx.readthedocs.io/
- ``weasyprint``: https://weasyprint.org/
- ``xhtml2pdf``: https://xhtml2pdf.readthedocs.io/
