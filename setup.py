#!/usr/bin/env python
# setup.py

"""
cardinal_pythonlib setup file

To use:

    python setup.py sdist

    twine upload dist/*

To install in development mode:

    pip install -e .

"""

from setuptools import setup, find_packages
from codecs import open
from os import path

from cardinal_pythonlib.version_string import VERSION_STRING

PACKAGE_NAME = "cardinal_pythonlib"
THIS_DIR = path.abspath(path.dirname(__file__))
README_FILE = path.join(THIS_DIR, 'README.rst')  # read


# =============================================================================
# Get the long description from the README file
# =============================================================================

with open(README_FILE, encoding='utf-8') as f:
    long_description = f.read()


# =============================================================================
# Specify requirements
# =============================================================================

REQUIREMENTS = [
    # - Include most things that are imported without "try / except
    #   ImportError" handling.
    # - Include as few version requirements as possible.
    # - Keep it to pure-Python packages (for e.g. Windows installation with no
    #   compiler).
    # - Keep it to SMALL packages.
    # - SEE ALSO external_dependencies.rst

    "alembic",
    "appdirs>=1.4.0",
    "beautifulsoup4",  # "import bs4" or "from bs4 import ..."
    "colorlog",
    "isodate>=0.5.4",
    "numpy>=1.20.0",  # 1.20.0 required for numpy.typing
    "openpyxl",
    "pandas",
    "pendulum>=2.1.1",
    "prettytable",
    "psutil",
    "pygments",
    "pyparsing",
    "PyPDF2",
    "python-dateutil",  # "import dateutil"
    "scipy",
    "semantic-version",
    "SQLAlchemy",
    "sqlparse",
]

NOTES_RE_OTHER_REQUIREMENTS = """

# -----------------------------------------------------------------------------
# Use the PyPi index:
# -----------------------------------------------------------------------------
--index-url https://pypi.python.org/simple/


# -----------------------------------------------------------------------------
# The following are NOT HANDLED GRACEFULLY; their absence will cause a runtime
# ImportError, but we don't make them requirements as they need a compiler to
# install (and one might want to use the rest of the library without them).
# -----------------------------------------------------------------------------
# - SEE ALSO external_dependencies.rst

# arrow
# bcrypt
# colander
# deform
# Django>=2.0.0
# dogpile.cache
# pyramid
# webob  # installed by pyramid


# -----------------------------------------------------------------------------
# The following are OPTIONAL; their absence will be handled gracefully, so
# they are not requirements, but we note them here:
# -----------------------------------------------------------------------------
# - SEE ALSO external_dependencies.rst

# mmh3
# pdfkit
# pdfminer
# pypiwin32
# pyth
# python-docx   # "import docx"
# weasyprint
# xhtml2pdf


# -----------------------------------------------------------------------------
# FOR LIBRARY DEVELOPMENT
# -----------------------------------------------------------------------------

# sphinx
# sphinx_rtd_theme
# twine

# -----------------------------------------------------------------------------
# NO LONGER REQUIRED (but worth commenting on for now)
# -----------------------------------------------------------------------------

# DATABASE DRIVERS:
# jaydebeapi  -- in deprecated rnc_db module only
# mysql-python  # "import MySQLdb"  -- in deprecated rnc_db module only
# mysqlclient  # "import MySQLdb"  -- in deprecated rnc_db module only
# pymysql  -- in deprecated rnc_db module only
# pyodbc  -- in deprecated rnc_db module only
# pypyodbc  -- in deprecated rnc_db module only

"""


# =============================================================================
# setup args
# =============================================================================

setup(
    name=PACKAGE_NAME,

    version=VERSION_STRING,

    description='Miscellaneous Python libraries',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/RudolfCardinal/pythonlib',

    # Author details
    author='Rudolf Cardinal',
    author_email='rudolf@pobox.com',

    # Choose your license
    license='Apache License 2.0',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache Software License',

        'Natural Language :: English',

        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',

        'Topic :: Software Development :: Libraries',
    ],

    keywords='cardinal',

    packages=find_packages(),  # finds all the .py files in subdirectories

    install_requires=REQUIREMENTS,

    entry_points={
        'console_scripts': [
            # Format is 'script=module:function".

            # openxml
            'cardinalpythonlib_find_bad_openxml=cardinal_pythonlib.openxml.find_bad_openxml:main',  # noqa
            'cardinalpythonlib_find_recovered_openxml=cardinal_pythonlib.openxml.find_recovered_openxml:main',  # noqa
            'cardinalpythonlib_grep_in_openxml=cardinal_pythonlib.openxml.grep_in_openxml:main',  # noqa
            'cardinalpythonlib_pause_process_by_disk_space=cardinal_pythonlib.openxml.pause_process_by_disk_space:main',  # noqa

            # tools
            'cardinalpythonlib_backup_mysql_database=cardinal_pythonlib.tools.backup_mysql_database:main',  # noqa
            'cardinalpythonlib_bulk_email=cardinal_pythonlib.bulk_email.main:main',  # noqa
            'cardinalpythonlib_convert_athena_ohdsi_codes=cardinal_pythonlib.tools.convert_athena_ohdsi_codes:main',  # noqa
            'cardinalpythonlib_convert_mdb_to_mysql=cardinal_pythonlib.tools.convert_mdb_to_mysql:main',  # noqa
            'cardinalpythonlib_estimate_mysql_memory_usage=cardinal_pythonlib.tools.estimate_mysql_memory_usage:main',  # noqa
            'cardinalpythonlib_list_all_file_extensions=cardinal_pythonlib.tools.list_all_file_extensions:main',  # noqa
            'cardinalpythonlib_merge_csv=cardinal_pythonlib.tools.merge_csv:main',  # noqa
            'cardinalpythonlib_pdf_to_booklet=cardinal_pythonlib.tools.pdf_to_booklet:main',  # noqa
            'cardinalpythonlib_remove_duplicate_files=cardinal_pythonlib.tools.remove_duplicate_files:main',  # noqa

            # other
            'cardinalpythonlib_chebi=cardinal_pythonlib.chebi:main',
            'cardinalpythonlib_email=cardinal_pythonlib.email.sendmail:main',
            'cardinalpythonlib_extract_text=cardinal_pythonlib.extract_text:main',  # noqa
        ],
    },
)
