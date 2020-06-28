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
# https://packaging.python.org/en/latest/distributing/#working-in-development-mode
# http://python-packaging-user-guide.readthedocs.org/en/latest/distributing/
# http://jtushman.github.io/blog/2013/06/17/sharing-code-across-applications-with-python/  # noqa

import argparse
from setuptools import setup, find_packages
from codecs import open
from io import StringIO
from os import path
import sys

from cardinal_pythonlib.version_string import VERSION_STRING

THIS_DIR = path.abspath(path.dirname(__file__))
README_FILE = path.join(THIS_DIR, 'README.rst')  # read
REQUIREMENTS_FILE = path.join(THIS_DIR, 'requirements.txt')  # written

# -----------------------------------------------------------------------------
# Get the long description from the README file
# -----------------------------------------------------------------------------
with open(README_FILE, encoding='utf-8') as f:
    long_description = f.read()

# -----------------------------------------------------------------------------
# Nasty
# -----------------------------------------------------------------------------

REQUIREMENTS_TEXT = """
# This file is AUTOMATICALLY WRITTEN BY setup.py; DO NOT EDIT IT.
# We only do this so PyCharm knows the requirements too.

# =============================================================================
# Use the PyPi index:
# =============================================================================
--index-url https://pypi.python.org/simple/

# =============================================================================
# Actual requirements
# =============================================================================
# - Include most things that are imported without "try / except ImportError"
#   handling.
# - Include as few version requirements as possible.
# - Keep it to pure-Python packages (for e.g. Windows installation with no 
#   compiler).
# - Keep it to SMALL packages.
# - SEE ALSO external_dependencies.rst

alembic
appdirs>=1.4.0
beautifulsoup4  # "import bs4" or "from bs4 import ..."
colorlog
isodate>=0.5.4
numpy
openpyxl
pandas
pendulum>=2.0.0
prettytable
psutil
pygments
pyparsing
PyPDF2
python-dateutil  # "import dateutil"
scipy
semantic-version
SQLAlchemy
sqlparse


# =============================================================================
# The following are NOT HANDLED GRACEFULLY; their absence will cause a runtime
# ImportError, but we don't make them requirements as they need a compiler to
# install (and one might want to use the rest of the library without them).
# =============================================================================
# - SEE ALSO external_dependencies.rst

# arrow
# bcrypt
# colander
# deform
# Django>=2.0.0
# dogpile.cache
# pyramid
# webob  # installed by pyramid


# =============================================================================
# The following are OPTIONAL; their absence will be handled gracefully, so
# they are not requirements, but we note them here:
# =============================================================================
# - SEE ALSO external_dependencies.rst

# mmh3
# pdfkit
# pdfminer
# pypiwin32
# pyth
# python-docx   # "import docx"
# weasyprint
# xhtml2pdf


# =============================================================================
# FOR LIBRARY DEVELOPMENT
# =============================================================================

# sphinx
# sphinx_rtd_theme
# twine

# =============================================================================
# NO LONGER REQUIRED (but worth commenting on for now)
# =============================================================================

# DATABASE DRIVERS:
# jaydebeapi  -- in deprecated rnc_db module only
# mysql-python  # "import MySQLdb"  -- in deprecated rnc_db module only
# mysqlclient  # "import MySQLdb"  -- in deprecated rnc_db module only
# pymysql  -- in deprecated rnc_db module only
# pyodbc  -- in deprecated rnc_db module only
# pypyodbc  -- in deprecated rnc_db module only

"""

# REMEMBER: code that runs here needs to cope with the INSTALLATION situation
# as well as the PACKAGE CREATION situation.

requirements = []
with StringIO(REQUIREMENTS_TEXT) as f:
    for line in f.readlines():
        line = line.strip()
        if (not line) or line.startswith('#') or line.startswith('--'):
            continue
        requirements.append(line)


EXTRAS_ARG = 'extras'
parser = argparse.ArgumentParser()
parser.add_argument(
    '--' + EXTRAS_ARG, action='store_true',
    help=(
        "USE THIS TO CREATE PACKAGES (e.g. 'python setup.py sdist --{}. "
        "Copies extra info in.".format(EXTRAS_ARG)
    )
)
our_args, leftover_args = parser.parse_known_args()
sys.argv[1:] = leftover_args

if getattr(our_args, EXTRAS_ARG):
    # Here's where we do the extra stuff.
    with open(REQUIREMENTS_FILE, 'wt') as reqfile:
        reqfile.write(REQUIREMENTS_TEXT)


# -----------------------------------------------------------------------------
# setup args
# -----------------------------------------------------------------------------
setup(
    name='cardinal_pythonlib',

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
        # 'Programming Language :: Python :: 2',
        # 'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        # 'Programming Language :: Python :: 3.2',
        # 'Programming Language :: Python :: 3.3',
        # 'Programming Language :: Python :: 3.4',
        # 'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',

        'Topic :: Software Development :: Libraries',
    ],

    keywords='cardinal',

    packages=find_packages(),  # finds all the .py files in subdirectories

    install_requires=requirements,  # see requirements.txt

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
