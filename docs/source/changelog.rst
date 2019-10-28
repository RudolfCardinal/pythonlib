..  cardinal_pythonlib/docs/source/changelog.rst

..  Copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).
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

Quick links:

- :ref:`2017 <changelog_2017>`
- :ref:`2018 <changelog_2018>`
- :ref:`2019 <changelog_2019>`


.. _changelog_2017:

2017
~~~~

**0.2.7, 2017-04-28**

- Fixed bug in :mod:`cardinal_pythonlib.extract_text` that was using
  :func:`cardinal_pythonlib.extract_text.get_file_contents` as a converter when
  it wasn't accepting generic ``**kwargs``; now it is.

**0.2.8, 2017-04-28**

- Fixed DOCX table processing bug, in
  :func:`cardinal_pythonlib.extract_text.docx_process_table`.

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


.. _changelog_2018:

2018
~~~~

**1.0.9 to 1.0.10, 2018-01-05 + 2018-02-19**

- Additions to :mod:`cardinal_pythonlib.datetimefunc` and improvements to
  :mod:`cardinal_pythonlib.sqlalchemy.dump` for CamCOPS. Addition of
  :mod:`cardinal_pythonlib.slurm`.

**1.0.11, 2018-02-23**

- Automatic JSON encoding of ``Pendulum`` objects; see
  :mod:`cardinal_pythonlib.json.serialize`.
- Some DSP code.

**1.0.12, 2018-03-08**

- Fixed :func:`cardinal_pythonlib.datetimefunc.coerce_to_datetime` so it
  coerces Pendulum to datetime too.

**1.0.13, 2018-03-08**

- :mod:`cardinal_pythonlib.argparse_func`:
  :func:`cardinal_pythonlib.argparse_func.str2bool`,
  :func:`cardinal_pythonlib.argparse_func.percentage`,
  :func:`cardinal_pythonlib.argparse_func.positive_int`.

**1.0.14, 2018-05-01**

- ``**kwargs`` options to :func:`cardinal_pythonlib.json.serialize.json_encode`

**1.0.15, 2018-05-04**

- There was a bad character in a comment in
  :mod:`cardinal_pythonlib.winservice`; fixed.

**1.0.16, 2018-05-22**

- New file :mod:`cardinal_pythonlib.sqlalchemy.engine_func`
- JSON serialization of ``pendulum.Date``
- ``@register_enum_for_json`` in :mod:`cardinal_pythonlib.json.serialize`.

**1.0.17, 2018-05-27**

- lazy dictionaries

**1.0.18, 2018-06-29**

- update for Django 2.0+
- update for Pendulum 2.0+

**1.0.19 to 1.0.21, 2018-07-01 to 2018-07-02**

- :mod:`cardinal_pythonlib.psychiatry.drugs`
- version assertion commands (for R access via reticulate)

**1.0.22, 2018-07-07**

- ``as_sql`` (etc.) options to
  :func:`cardinal_pythonlib.sqlalchemy.alembic_func.upgrade_database`

**1.0.23, 2018-07-23**

- separation of version string for ``setup.py``

**1.0.24, 2018-09-11 to 2018-09-14**

- extra debug option (``debug_wkhtmltopdf_args``) for
  :func:`cardinal_pythonlib.pdf.get_pdf_from_html`
- Sphinx autodocumentation.
- ``create_base64encoded_randomness()`` removed from
  :mod:`cardinal_pythonlib.crypto` as was duplicated as
  :func:`cardinal_pythonlib.randomness.create_base64encoded_randomness`.
- removed all requirements (temporarily? permanently?) as we were having
  problems installing on machines with wrong compiler versions or absent
  compilers, but didn't need those specific sub-dependencies; so consequence is
  that packages that use this software need to add additional requirements.

**1.0.25, 2018-09-16**

- Dependencies put back, except dependency on ``regex`` removed.
- Further documentation.
- Duplicate hash-related functions removed from
  :mod:`cardinal_pythonlib.crypto`; better versions were in
  :mod:`cardinal_pythonlib.hash`.
- Bugfix to :func:`cardinal_pythonlib.sqlalchemy.schema.is_sqlatype_date` for
  more recent versions of SQLAlchemy (e.g. 1.2.11). Error was:
  ``AttributeError: module 'sqlalchemy.sql.sqltypes' has no attribute
  '_DateAffinity'``.

**1.0.26, 2018-09-21**

- Bugfix to
  :func:`cardinal_pythonlib.sqlalchemy.orm_inspect.deepcopy_sqla_object`;
  crash if ``objmap`` was ``None``.

**1.0.26, 2018-09-22**

- Make everything except pure-Python dependencies optional.
- Work out what those are with
  :func:`cardinal_pythonlib.modules.is_c_extension`.
- public docs at https://cardinalpythonlib.readthedocs.io/

**1.0.27 to 1.0.29, 2018-09-23 to 2018-09-28**

- :mod:`cardinal_pythonlib.sphinxtools` to help with building documentation
- added ``pygments`` dependency

**1.0.30, 2018-10-10**

- :mod:`cardinal_pythonlib.email.mailboxpurge.`
- ``emailfunc.py`` renamed to :mod:`cardinal_pythonlib.email.sendmail`

**1.0.32, 2018-10-16**

- :mod:`cardinal_pythonlib.typing_helpers`

- updated
  :class:`cardinal_pythonlib.django.fields.restrictedcontentfile.ContentTypeRestrictedFileField`
  to cope with Django 2.1.

- improvements to :class:`cardinal_pythonlib.sphinxtools.AutodocIndex` in
  relation to filename glob processing for ``skip_globs``

**1.0.33, 2018-11-02**

- bugfix to
  :func:`cardinal_pythonlib.sqlalchemy.schema.convert_sqla_type_for_dialect`;
  this is meant to autoconvert ``TIMESTAMP`` fields in SQL Server, but it was
  checking against :class:`sqlalchemy.sql.sqltypes.TIMESTAMP` and should have
  been checking against :class:`sqlalchemy.dialects.mssql.base.TIMESTAMP`.

**1.0.34, 2018-11-06**

- Bugfix to :mod:`cardinal_pythonlib.psychiatry.drugs`; amitriptyline was being
  listed as an FGA.
- New code in that module to calculate SQL ``LIKE`` clauses; see docstring.

**1.0.35 to 1.0.36, 2018-11-06**

- Type hint :class:`cardinal_pythonlib.typing_helpers.Pep249DatabaseCursorType`

**1.0.37, 2018-11-10**

- Clarified :class:`cardinal_pythonlib.colander_utils.OptionalPendulumNode` as
  to timezone, and added the synonym
  :class:`cardinal_pythonlib.colander_utils.OptionalPendulumNodeLocalTZ` and
  the UTC version
  :class:`cardinal_pythonlib.colander_utils.OptionalPendulumNodeUTC`.

- In :func:`cardinal_pythonlib.sqlalchemy.alembic_func.upgrade_database`,
  which allowed upgrades only (not downgrades), pointless decorative parameter
  ``operation_name`` removed.

- Added :func:`cardinal_pythonlib.sqlalchemy.alembic_func.downgrade_database`.

- Made :func:`cardinal_pythonlib.sqlalchemy.core_query.fetch_all_first_values`
  a bit more generic.

**1.0.38, 2018-11-26**

- Bugfix to "missing tkinter" detection code in :mod:`cardinal_pythonlib.ui`.

**1.0.39, 2018-12-02**

- Changed the time options to the date/time widgets in
  :class:`cardinal_pythonlib.colander_utils.OptionalPendulumNodeLocalTZ` and
  :class:`cardinal_pythonlib.colander_utils.OptionalPendulumNodeUTC`. The
  previous problem was that a 12-hour format (e.g. "11:30 PM") was being used,
  and this re-interpreted incoming (Python) 24-hour values as morning times.

**1.0.40, 2018-12-11**

- Bugfix to :meth:`cardinal_pythonlib.psychiatry.drugs.Drug.regex`; was using
  ``self._regex_text`` but should have been ``self.regex_text``.
  Also fixed example (was mis-importing).

**1.0.41, 2018-12-17 to 2018-12-30**

- Improvements to :func:`cardinal_pythonlib.email.sendmail.send_email`.
- New function
  :func:`cardinal_pythonlib.datetimefunc.pendulum_to_utc_datetime_without_tz`.
- Config file parsers report the section for missing/improper parameters.
- More consistent use of brace-style deferred-processing logs internally, and
  :func:`cardinal_pythonlib.logs.get_brace_style_log_with_null_handler`.
- Clean pass through PyCharm 2018.3 code inspector.
- Improved "hard kill" function for Windows in
  :meth:`cardinal_pythonlib.winservice.ProcessManager.stop`.
- :class:`cardinal_pythonlib.sqlalchemy.list_types.StringListType` no longer
  writes trailing newlines. This is a back-compatible change.
- Advice added to
  :class:`cardinal_pythonlib.sqlalchemy.list_types.StringListType` about the
  slightly unusual behaviour of lists written to the database.
- Moved to the ``create_all_autodocs.py`` system.


.. _changelog_2019:

2019
~~~~

**1.0.42 to 1.0.45, 2019-01-04**

- Minor fix: ``__init__.py`` missing from :mod:`cardinal_pythonlib.email`;
  required for Python 3.5.
- Some bugfixes to :mod:`cardinal_pythonlib.email.sendmail` for e-mail servers
  not supporting login (!).

**1.0.46, 2019-01-19**

- Option to :func:`cardinal_pythonlib.buildfunc.untar_to_directory` to perform
  the change of directory via Python, not via ``tar`` -- because Cygwin ``tar``
  v1.29 falls over when given a Windows path for its ``-C`` (or
  ``--directory``) option.

**1.0.47, 2019-02-09**

- :func:`cardinal_pythonlib.extract_text.document_to_text` raises
  :exc:`ValueError` if a filename is passed and the file dosn't exist (or isn't
  a file). This is better than relying on the slightly less predictable
  behaviour of the various external tools.

**1.0.48 to 1.0.49, 2019-03-24**

- Optional `joiner` parameter to formatting functions in
  :mod:`cardinal_pythonlib.reprfunc`; extra options to
  :func:`cardinal_pythonlib.reprfunc.auto_str`.

- Additional tweaks to :class:`cardinal_pythonlib.sphinxtools.AutodocIndex`.

**1.0.50, 2019-04-05**

- "Change directory" option to
  :func:`cardinal_pythonlib.tools.backup_mysql_database.main`.

- Change to
  :func:`cardinal_pythonlib/psychiatry/treatment_resistant_depression.two_antidepressant_episodes_single_patient`
  as agreed on 2019-03-28 (Stewart, Broadbent, Cardinal) such that if
  antidepressant A "finishes" on the *same* day as B starts, that counts
  (previously, B needed to start 1 day later). Hard-coded change.

- New module :mod:`cardinal_pythonlib.interval`.

- New module :mod:`cardinal_pythonlib.psychiatry.timeline`.

- A couple of bad escape sequences fixed (should have been raw strings), in
  :data:`cardinal_pythonlib.nhs.WHITESPACE_REGEX`,
  :func:`cardinal_pythonlib.tools.pdf_to_booklet.get_page_count`,
  :func:`cardinal_pythonlib.sort.natural_keys`,
  :data:`cardinal_pythonlib.rnc_db._QUERY_VALUE_REGEX`, and
  :func:`cardinal_pythonlib.rnc_web.make_urls_hyperlinks`. I think the PyCharm
  inspector has had an upgrade.

**1.0.51, 2019-04-23**

- Bugfix to :mod:`cardinal_pythonlib.winservice` which checked
  ``if os.environ["_SPHINX_AUTODOC_IN_PROGRESS"]`` when it meant
  ``if os.environ.get("_SPHINX_AUTODOC_IN_PROGRESS")``, leading to a potential
  crash.

- Similar fix to :mod:`cardinal_pythonlib.django.middleware`.

**1.0.52, 2019-04-23**

- New module :mod:`cardinal_pythonlib.sqlalchemy.sqlserver`.

**1.0.53, 2019-04-27**

- New MIME types.

- Duration handlers in :mod:`cardinal_pythonlib.datetimefunc`,
  including ISO-8601 representations of duration.

- Extra small functions for ``colander`` in
  :mod:`cardinal_pythonlib.colander_utils`.

**1.0.54, 2019-06-14**

- :func:`cardinal_pythonlib.randomness.coin`.

- :class:`cardinal_pythonlib.dicts.HashableDict`.

**1.0.55, 2019-06-15**

- Bugfix to aspects of logging in :mod:`cardinal_pythonlib.buildfunc`

- :mod:`cardinal_pythonlib.rate_limiting`

**1.0.56 (buggy), 1.0.57, 2019-06-18**

- Build function updates. Avoid 1.0.56, it has a stupid bug confusing tar/git.

**1.0.58 (2019-06-29)**

- :mod:`cardinal_pythonlib.probability`

**1.0.59 (2019-07-02)**

- :func:`cardinal_pythonlib.maths_py.round_sf`

**1.0.60 (2019-08-06)**

- Bugfixes to log probability handling in
  :mod:`cardinal_pythonlib.probability`: (a)
  :func:`cardinal_pythonlib.probability.log10` was just plain wrong and
  returned ln(x) instead of log10(x); (b)
  :func:`cardinal_pythonlib.probability.log_probability_from_log_odds` used
  :func:`math.log` rather than using the internal version that treats log(0) as
  ``-inf``.

**1.0.61 (2019-08-19)**

- Improvement to :func:`cardinal_pythonlib.django.serve.serve_file` so that it
  won't crash if the ``XSENDFILE`` variable is not present in the Django
  settings (defaulting to False).

**1.0.62 (2019-08-31)**

- Updates to :mod:`cardinal_pythonlib.httpconst`

**1.0.63 (2019-09-01)**

- ``default_content_type`` parameters in
  :mod:`cardinal_pythonlib.django.serve`.
- bugfix to :func:`cardinal_pythonlib.exceptions.die` (log failing with
  messages that included braces).

**1.0.64 (2019-09-29)**

- :mod:`cardinal_pythonlib.compression`
- :mod:`cardinal_pythonlib.pyramid.constants`
- :mod:`cardinal_pythonlib.pyramid.compression`
- :mod:`cardinal_pythonlib.pyramid.requests`

**1.0.65 (2019-09-30)**

- :mod:`cardinal_pythonlib.sql.validation`, enabling the use of these functions
  without the deprecated - :mod:`cardinal_pythonlib.rnc_db`.

**1.0.66 to 1.0.71 (2019-10-06 to 2019-10-07)**

- ``rstrip`` argument to
  :class:`cardinal_pythonlib.extract_text.TextProcessingConfig` config class,
  used by :func:`cardinal_pythonlib.extract_text.document_to_text`.
- Renamed current ``plain`` behaviour in that module to ``semiplain``, and
  added ``plain`` which is plainer (and doesn't use PrettyTable).
- Fixed DOCX word-wrapping bug (wasn't wrapping plain paragraphs).
- UTF-8 characters used for tabular markings (see comments in
  :func:`cardinal_pythonlib.extract_text.docx_process_table`.
- :mod:`cardinal_pythonlib.athena_ohdsi`
- :mod:`cardinal_pythonlib.snomed`
- ``cardinalpythonlib_`` prefix to command-line tools
- **Minimum Python version is now 3.6,** allowing f-strings.

**1.0.72 to 1.0.73 (to 2019-10-10)**

- Speedup to Athena OHDSI code extraction.
- Renaming of core wordwrapping function to
  :func:`cardinal_pythonlib.extract_text.wordwrap` (otherwise confusing
  reference from CRATE).

**1.0.74 (2019-10-24)**

- Add ``appdirs`` package requirement.
- :mod:`cardinal_pythonlib.chebi` (note that ``libchebipy`` is imported but
  not required in the package)

  - Problem with ``libchebipy`` as it imported ``requests`` which imported
    ``email.parser`` which got upset by my ``email`` directory. It seems that
    there should be no file or subdirectory that clashes with a Python standard
    library -- or potentially any other? Seems a bit daft. See:

    - https://stackoverflow.com/questions/6861818/unable-to-import-pythons-email-module-at-all/6862236
    - https://docs.python.org/3/whatsnew/2.5.html#pep-328-absolute-and-relative-imports
    - https://www.evanjones.ca/python-name-clashes.html

    Ah, no -- it's only a problem if you execute one of the
    ``cardinal_pythonlib`` files from its own directory. Avoid that!

**1.0.75 to 1.0.77 (2019-10-25 to 2019-10-26)**

- ChEBI lookup improvements.
- Added :class:`cardinal_pythonlib.dicts.CaseInsensitiveDict`.
