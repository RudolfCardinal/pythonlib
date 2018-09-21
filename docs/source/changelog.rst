..  cardinal_pythonlib/docs/source/changelog.rst

..  Copyright © 2009-2018 Rudolf Cardinal (rudolf@pobox.com).
    .
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
    .
        http://www.apache.org/licenses/LICENSE-2.0
    .
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.


Change history
--------------

*RECENT VERSION HISTORY*

First started in 2009.

**0.2.7, 2017-04-28**

- Fixed bug in ``rnc_extract_text`` that was using ``get_file_contents()`` as a
  converter when it wasn't accepting generic ``**kwargs``; now it is.

**0.2.8, 2017-04-28**

- Fixed DOCX table processing bug, in ``docx_process_table()``.

**0.2.10, 2017-04-29**

- Text fetch (for converters) was returning bytes, not str; fixed.

**0.2.11, 2017-04-29**

- Encoding auto-detection for text extraction from files.

**0.2.12 to 0.2.13, 2017-05-02**

- More file types support for simple text extraction.
- Better encoding support.

**1.0.0, 2017-08-05**

- Consolidation of common functions from multiple projects to reduce code
  duplication. Some modules renamed.

**1.0.1, 2017-08-14**
- PyPI/``setup.py`` bugfix (not all subpackages were uploaded).

**1.0.2, 2017-08-20 onwards**
- Metaclass functions added.
- Extensions to SQLAlchemy utility functions.

**1.0.3, 2017-10-18**
- Several small changes for CamCOPS.

**... to 1.0.8, 2017-11-29**
- Similarly.

**1.0.9 to 1.0.10, 2018-01-05 + 2018-02-19**

- Additions to ``datetimefunc.py`` and improvements to ``sqlalchemy/dump.py`` for
  CamCOPS. Addition of ``slurm.py``.

**1.0.11, 2018-02-23**

- Automatic JSON encoding of ``Pendulum`` objects; see serialize.py
- Some DSP code.

**1.0.12, 2018-03-08**

- Fixed ``coerce_to_datetime()`` so it coerces Pendulum to datetime too.

**1.0.13, 2018-03-08**

- ``argparse_func``: ``str2bool()``, ``percentage()``, ``positive_int()``

**1.0.14, 2018-05-01**

- ``**kwargs`` options to ``json_encode()``

**1.0.15, 2018-05-04**

- There was a bad character in a comment in ``winservice.py``; fixed.

**1.0.16, 2018-05-22**

- New file ``sqlalchemy/engine_func.py``
- JSON serialization of ``pendulum.Date``
- ``@register_enum_for_json``

**1.0.17, 2018-05-27**

- lazy dictionaries

**1.0.18, 2018-06-29**

- update for Django 2.0+
- update for Pendulum 2.0+

**1.0.19 to 1.0.21, 2018-07-01 to 2018-07-02**

- ``psychiatry/drugs.py``
- version assertion commands (for R access via reticulate)

**1.0.22, 2018-07-07**

- ``as_sql`` (etc.) options to ``alembic_func.upgrade_database``

**1.0.23, 2018-07-23**

- separation of version string for ``setup.py``

**1.0.24, 2018-09-11 to 2018-09-14**

- extra debug option (``debug_wkhtmltopdf_args``) for ``get_pdf_from_html``
- Sphinx autodocumentation.
- ``create_base64encoded_randomness()`` removed from ``crypto.py`` as was
  duplicated in ``randomness.py``.
- removed all requirements (temporarily? permanently?) as we were having
  problems installing on machines with wrong compiler versions or absent
  compilers, but didn't need those specific sub-dependencies; so consequence is
  that packages that use this software need to add additional requirements.

**1.0.25, 2018-09-16**

- Dependencies put back, except dependency on ``regex`` removed.
- Further documentation.
- Duplicate hash-related functions removed from ``crypto.py``; better versions
  were in ``hash.py``.
- Bugfix to :func:`cardinal_pythonlib.sqlalchemy.schema.is_sqlatype_date` for
  more recent versions of SQLAlchemy (e.g. 1.2.11).

**1.0.26, 2018-09-21**

- Bugfix to
  :func:`cardinal_pythonlib.sqlalchemy.orm_inspect.deepcopy_sqla_object`;
  crash if ``objmap`` was ``None``.