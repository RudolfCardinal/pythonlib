
..  cardinal_pythonlib/docs/source/changelog.rst

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


Change history
--------------

*RECENT VERSION HISTORY*

First started in 2009.

Quick links:

- :ref:`2017 <changelog_2017>`
- :ref:`2018 <changelog_2018>`
- :ref:`2019 <changelog_2019>`
- :ref:`2020 <changelog_2020>`
- :ref:`2021 <changelog_2021>`
- :ref:`2022 <changelog_2022>`
- :ref:`2023 <changelog_2023>`
- :ref:`2024 <changelog_2024>`
- :ref:`2025 <changelog_2025>`


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

**1.0.78 to 1.0.81 (2019-11-17)**

- :func:`cardinal_pythonlib.debugging.pdb_run` returns its function result.
- :data:`cardinal_pythonlib.text.UNICODE_CATEGORY_STRINGS` replaced by
  :func:`cardinal_pythonlib.text.get_unicode_category_strings`. This is a large
  data item (~5 Mb) that should only be generated on request.
- New function :func:`cardinal_pythonlib.text.get_unicode_characters`.
- New function :func:`cardinal_pythonlib.process.nice_call`, to clean up
  children better when the calling parent receives a Ctrl-C (SIGINT).
- New function :func:`cardinal_pythonlib.fileops.get_directory_contents_size`
- Bug fix https://github.com/RudolfCardinal/pythonlib/issues/1
  :func:`cardinal_pythonlib.sqlalchemy.alembic_func.create_database_migration_numbered_style`
  now ignores backup files (and anything else that doesn't look like a
  migration file).

**1.0.82 (2019-11-20)**

- :mod:`cardinal_pythonlib.json.typing_helpers`

**1.0.83 (2019-12-03)**

- :func:`cardinal_pythonlib.maths_py.sum_of_integers_in_inclusive_range`
- :func:`cardinal_pythonlib.maths_py.n_permutations`
- type hint accepts floats to
  :func:`cardinal_pythonlib.rate_limiting.rate_limited`


.. _changelog_2020:

2020
~~~~

**1.0.84 (2020-01-11 to 2020-01-19)**

- Create ``cardinal_pythonlib.__version__``
- Copyright years to 2020.
- ``cardinalpythonlib_convert_mdb_to_mysql`` tool.

**1.0.85 (2020-02-03)**

- :func:`cardinal_pythonlib.file_io.gen_noncomment_lines`.

**1.0.86 (2020-04-20)**

- :mod:`cardinal_pythonlib.contexts`
- :mod:`cardinal_pythonlib.iterhelp`
- :mod:`cardinal_pythonlib.parallel`
- :mod:`cardinal_pythonlib.profile`
- Speedup to :func:`cardinal_pythonlib.randomness.coin`

**1.0.87 (2020-04-24)**

- Removed timing overheads from :mod:`cardinal_pythonlib.hash`.

**1.0.88 (2020-04-24)**

- Optimizations for :mod:`cardinal_pythonlib.probability`.

**1.0.89 (2020-06-16, MB)**

- Fix :func:`cardinal_pythonlib.datetimefunc.coerce_to_pendulum` when coercing
  ``datetime.date`` objects; the timezone was being lost.

**1.0.90 (2020-06-20)**

- :mod:`cardinal_pythonlib.docker`

**1.0.91 (2020-06-28)**

- Removed ``tkinter`` dependence via :mod:`cardinal_pythonlib.ui_commandline`.

**1.0.92 (2020-06-28)**

- Made several other large dependencies optional.

**1.0.93 (2020-07-12)**

- Renamed some functions in :mod:`cardinal_pythonlib.interval` to make UK
  specificity clear.

**1.0.94 (2020-07-21)**

- Fixes for Django 3.

  - Remove the final ``context`` parameter from all ``from_db_value`` functions
    for custom fields, as per
    https://docs.djangoproject.com/en/2.0/releases/2.0/#context-argument-of-field-from-db-value-and-expression-convert-value.
    Otherwise you get errors like:
    ``from_db_value() missing 1 required positional argument: 'context'``.

**1.0.95 (2020-09-21)**

- Some more convenience functions for calling subprocesses and checking
  environment variables:

  - :mod:`cardinal_pythonlib.sysops`
  - :func:`cardinal_pythonlib.subproc.check_call_verbose`

**1.0.96 (2020-09-28)**

- :mod:`cardinal_pythonlib.wsgi.headers_mw`
- :func:`cardinal_pythonlib.enumlike.keys_descriptions_from_enum`
- :class:`cardinal_pythonlib.enumlike.EnumLower`

**1.0.97 (2020-10-04)**

- :class:`cardinal_pythonlib.colander_utils.OptionalEmailNode`
- Some ``NoReturn`` type hinting.
- Log level configurable in :mod:`cardinal_pythonlib.configfiles` (and default
  DEBUG rather than WARNING).
- Better HTTP header handling in
  :class:`cardinal_pythonlib.wsgi.headers_mw.AddHeadersMiddleware`

**1.0.98 (to 2020-11-02)**

- :class:`cardinal_pythonlib.colander_utils.MandatoryEmailNode`
- workaround for HTTP 403 errors in
  :func:`cardinal_pythonlib.network.download`

**1.0.99 (2020-11-14)**

- Bugfix to :func:`cardinal_pythonlib.docker.running_under_docker` (it left
  a file open).

**1.1.0 (2020-12-01)**

- :mod:`cardinal_pythonlib.counter`
- :mod:`cardinal_pythonlib.datamapping`
- :mod:`cardinal_pythonlib.spreadsheets`
- :func:`cardinal_pythonlib.randomness.generate_random_string`


.. _changelog_2021:

2021
~~~~

**1.1.1 to 1.1.2 (2021-02-21)**

- :mod:`cardinal_pythonlib.rounding`
- Decimal option in :mod:`cardinal_pythonlib.spreadsheets`, and some other
  minor spreadsheet-handling capabilities. Bugfix from 1.1.1 to 1.1.2.

**1.1.3 (2021-02-22 to 2021-03-15)**

- :mod:`cardinal_pythonlib.sqlalchemy.semantic_version_coltype`
- Minor tweaks to :mod:`cardinal_pythonlib.spreadsheets`.

**1.1.4 (2021-04-11)**

- Minor improvements to :mod:`cardinal_pythonlib.spreadsheets`.
- Fix UUID export in :mod:`cardinal_pythonlib.excel` and a related function.

**1.1.5 (2021-04-23 to 2021-05-22)**

- Minor improvements to :mod:`cardinal_pythonlib.spreadsheets`.
- fix ``enumlike.py`` to work with Python 3.9

**1.1.6 (2021-05-22)**

- Bump Pendulum to 2.1.1 or higher because earlier versions have a sort-of bug
  relating to durations: https://github.com/sdispater/pendulum/pull/482.
  I am not entirely convinced Pendulum has done this the right way. However, we
  can detect its behaviour and do sensible things with ISO duration
  conversions. Corresponding changes to ``datetimefunc.py``, plus better
  self-tests.

- Note, in general, the use of ``export PYTHONDEVMODE=1`` to ensure no
  additional ``DeprecationWarning`` messages come up.

**1.1.7 (2021-05-24)**

- Minor spreadsheet tweaks.

**1.1.8 (2021-10-04)**

- ``official_test_range`` option (also now the default) to
  :func:`cardinal_pythonlib.nhs.generate_random_nhs_number`
- ``MimeType.HTML``.

**1.1.9 (2021-10-04)**

- More helper functions in :mod:`cardinal_pythonlib.classes`.

**1.1.10 (2021-10-05)**

- :func:`cardinal_pythonlib.typing_helpers.with_typehint`
- :class:`cardinal_pythonlib.httpconst.HttpStatus`

**1.1.11 (2021-10-11 to 2021-10-13)**

- Simple bulk e-mail tool, ``cardinalpythonlib_bulk_email``.
- :mod:`cardinal_pythonlib.rpm`
- numpy to 1.20.0, mandating Python 3.7+

**1.1.12 (2021-10-18 to 2021-11-03)**

- Improved :func:`cardinal_pythonlib.email.sendmail.is_email_valid`
- Improved :mod:`cardinal_pythonlib.httpconst`
- :mod:`cardinal_pythonlib.tcpipconst`
- :mod:`cardinal_pythonlib.uriconst`

**1.1.13 (2021-11-09 to 2021-11-17)**

- ``ignore_none`` parameter to
  :func:`cardinal_pythonlib.spreadsheets.check_attr_all_same`,
  :func:`cardinal_pythonlib.spreadsheets.require_attr_all_same`,
  :func:`cardinal_pythonlib.spreadsheets.prefer_attr_all_same`. Default is
  ``False`` so no change required to existing code.

- use of ``time.clock()`` replaced by ``time.perf_counter()``. See
  https://www.webucator.com/article/python-clocks-explained/

**1.1.14 (2021-11-17 to 2021-11-18)**

- Extra MIME type constants.
- HTTP response objects for JSON.

**1.1.15 (2021-11-21)**

- :func:`cardinal_pythonlib.sqlalchemy.dialect.get_dialect_from_name`.

**1.1.16 (2021-12-08)**

- Improved error message for
  :func:`cardinal_pythonlib.enumlike.keys_descriptions_from_enum` when used
  with key case conversions but a case-insensitive Enum.

- ``REAL`` recognized as an SQL floating-point data type, as well as ``DOUBLE``
  and ``FLOAT``.


.. _changelog_2022:

2022
~~~~

**1.1.17 (2022-02-26)**

- :func:`cardinal_pythonlib.lists.delete_elements_by_index`
- Restructure internal tests (to separate code and use ``pytest``).

**1.1.18 (2022-03-02)**

- :func:`cardinal_pythonlib.datetimefunc.coerce_to_date`, and some more unit
  tests.

**1.1.19 (2022-04-27 to 2022-06-02)**

- Tool `cardinalpythonlib_explore_clang_format_config`.
- :func:`cardinal_pythonlib.fileops.concatenate`
- :class:`cardinal_pythonlib.fileops.FileWatcher`
- Rearranged unit tests -- one (non-critical) test of the dogpile.cache
  extensions is not now working; unclear why; change in how args/kwargs are
  being labelled?
- :func:`cardinal_pythonlib.psychiatry.simhelpers.gen_params_around_centre`
- Speedup and edge case handling improved for
  :func:`cardinal_pythonlib.probability.ln` and
  :func:`cardinal_pythonlib.probability.log10`.

**1.1.20 (2022-06-02)**

- No code change, but after uploading successfully with ``twine upload
  dist/FILE.tar.gz``, automatic or manual downloads failed with
  "SignatureDoesNotMatch" / "The request signature we calculated does not match
  the signature you provided. Check your Google secret key and signing method."
  Upgraded from twine==3.2.0 to twine==4.0.1 (with requests==2.27.1). No joy.
  But I think the problem is the site refusing downloads, not uploads.
  Try to download all from https://pypi.org/simple/cardinal-pythonlib/; works
  to v1.1.18, then stops working. However, it's also the same error message
  for garbage filename in the URL.
  Could it be this error?
  https://github.com/stevearc/pypicloud/issues/120

**1.1.21 (2022-06-05)**

- Still having PyPi problems.
- :func:`cardinal_pythonlib.nhs.is_test_nhs_number`

**1.1.22 (2022-08-10)**

- Fast RPM functions, using numba, specialized for the two-choice situation.

**1.1.23 (2022-08-16)**

- **BREAKING CHANGE**: The dictionary ``pygments_language_override`` passed to
  :class:`cardinal_pythonlib.sphinxtools.FileToAutodocument` and
  :class:`cardinal_pythonlib.sphinxtools.AutodocIndex` is now keyed on file
  specification, not file extension. So language can be specified on a per-file
  basis. Existing code should be changed so that for example ``".html"`` becomes
  ``"*.html"`` to override all HTML files.


.. _changelog_2023:

2023
~~~~

**1.1.24 (2023-02-15)**

- In :func:`cardinal_pythonlib.pdf.make_pdf_from_html`, take a copy of
  ``wkhtmltopdf_options``; this prevents a bug where calls using e.g. a
  temporary file as footer HTML then make the next call, with no footer, fail
  (because the footer filename was written back to the dict).

- ``pdf.py`` updated to use pypdf instead of PyPDF2, which is no longer
  supported.

**1.1.25 (2023-10-17)**

- Use ``rich_argparse`` for colourful help.

- Small tweaks (and a rather specific R script generator) re psychotropic
  medications.

- Removed defunct ``rnc_db`` module.

- Removed Python 3.7 support (end of life); added Python 3.10 support.

- Supported SQLAlchemy version now 1.4

.. _changelog_2024:

2024
~~~~

**1.1.26 (2024-03-03)**

- Fix ``AttributeError: 'Engine' object has no attribute 'schema_for_object'``
  when adding a full text index to an anonymised SQL Server database table.
  This bug has been present since the SQLAlchemy 1.4 upgrade in 1.1.25.

**1.1.27 (2024-07-15)**

- Fixes for Django 4.

  - Replace ugettext_* calls removed in Django 4.0.
    https://docs.djangoproject.com/en/4.2/releases/4.0/#features-removed-in-4-0

.. _changelog_2025:

2025
~~~~

**2.0.0 (2025-01-07)**

- Update for SQLAlchemy 2.

  ADDED:

  - cardinal_pythonlib.sqlalchemy.insert_on_duplicate.insert_with_upsert_if_supported
  - cardinal_pythonlib.sqlalchemy.core_query.get_rows_fieldnames_from_select

  REMOVED:

  - cardinal_pythonlib.sqlalchemy.insert_on_duplicate.InsertOnDuplicate

    Use insert_with_upsert_if_supported() instead.

  - cardinal_pythonlib.sqlalchemy.orm_query.get_rows_fieldnames_from_query

    This will now raise NotImplementedError. Use
    get_rows_fieldnames_from_select() instead. This reflects a core change in
    SQLAlchemy 2, moving towards the use of select() statements for all
    queries.

  SHOULDN'T BE NOTICEABLE:

  - cardinal_pythonlib.sqlalchemy.orm_query.CountStarSpecializedQuery has
    changed type. But operation is as before, assuming all you did with it
    was apply filters (if required) and execute.

  - Multiple internal changes to support SQLAlchemy 2.

**2.0.1 (2025-01-22)**

- Bugfix to ``cardinal_pythonlib.sqlalchemy.sqlserver`` functions as they
  were executing unconditionally, regardless of SQLAlchemy dialect (they should
  have been conditional to SQL Server).

**2.0.2 (2025-03-06)**

- Bugfix to
  :func:`cardinal_pythonlib.sqlalchemy.alembic_func.get_current_revision` where
  since SQLAlchemy 2.0, the database connection was persisting, resulting in a
  metadata lock.

- Bugfix to :func:`cardinal_pythonlib.extract_text.convert_pdf_to_txt` where
  ``pdftotext`` was unavailable. Also remove antique ``pyth`` support. And
  shift from unmaintained ``pdfminer`` to maintained ``pdfminer.six``. Also
  removed unused code around importing ``docx`` and ``docx2txt``.

- Add some back-compatibility with SQLAlchemy 1.4+ for testing.

- Improvements to ``merge_db``, including the option to ignore SQLAlchemy's
  default table dependency order and calculate another.

- Improve ability of Alembic support code to take a database URL.

**2.0.3 (2025-03-11)**

- Reinstate BIT and similar datatypes in the list of valid datatypes. Broken
  since v2.0.0.

- Allow ``db_url`` parameter to
  ``cardinal_pythonlib.sqlalchemy.alembic_func.create_database_migration_numbered_style``.

**2.0.4 (2025-03-17)**

- Fix :func:`cardinal_pythonlib.sqlalchemy.schema.execute_ddl` so that it always
  commits. Not all dialects commit automatically.

**2.0.5 (2025-04-07)**

- Add VARCHAR to valid Databricks types.

**2.1.0 (2025-05-13)**

- **BREAKING CHANGE**: Rename modules to avoid conflicts with the Python
  standard library:

   - :mod:`cardinal_pythonlib.email` is now :mod:`cardinal_pythonlib.email_utils`
   - :mod:`cardinal_pythonlib.json` is now :mod:`cardinal_pythonlib.json_utils`
   - :mod:`cardinal_pythonlib.profile` is now :mod:`cardinal_pythonlib.profiling`

- Add support for ``.eml`` files with attachments processed by supported
  document converters (``.docx``, ``.pdf``, ``.odt`` etc.) to
  :func:`cardinal_pythonlib.extract_text.document_to_text`.

**2.1.1 (2025-05-15)**

- Add support for Outlook ``.msg`` files with attachments processed by supported
  document converters (``.docx``, ``.pdf``, ``.odt`` etc.) to
  :func:`cardinal_pythonlib.extract_text.document_to_text`.
