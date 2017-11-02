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

from setuptools import setup, find_packages
from codecs import open
from os import path

from cardinal_pythonlib.version import VERSION

here = path.abspath(path.dirname(__file__))

# -----------------------------------------------------------------------------
# Get the long description from the README file
# -----------------------------------------------------------------------------
with open(path.join(here, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

# -----------------------------------------------------------------------------
# Nasty
# -----------------------------------------------------------------------------

requirements = []
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    for line in f.readlines():
        line = line.strip()
        if (not line) or line.startswith('#') or line.startswith('--'):
            continue
        requirements.append(line)

# -----------------------------------------------------------------------------
# setup args
# -----------------------------------------------------------------------------
setup(
    name='cardinal_pythonlib',

    version=VERSION,

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
        'Programming Language :: Python :: 3.5',

        'Topic :: Software Development :: Libraries',
    ],

    keywords='cardinal',

    packages=find_packages(),  # finds all the .py files in subdirectories

    install_requires=requirements,  # see requirements.txt

    entry_points={
        'console_scripts': [
            # Format is 'script=module:function".

            # openxml
            'find_bad_openxml=cardinal_pythonlib.openxml.find_bad_openxml:main',  # noqa
            'find_recovered_openxml=cardinal_pythonlib.openxml.find_recovered_openxml:main',  # noqa
            'grep_in_openxml=cardinal_pythonlib.openxml.grep_in_openxml:main',  # noqa
            'pause_process_by_disk_space=cardinal_pythonlib.openxml.pause_process_by_disk_space:main',  # noqa

            # tools
            'backup_mysql_database=cardinal_pythonlib.tools.backup_mysql_database:main',  # noqa
            'estimate_mysql_memory_usage=cardinal_pythonlib.tools.estimate_mysql_memory_usage:main',  # noqa
            'list_all_file_extensions=cardinal_pythonlib.tools.list_all_file_extensions:main',  # noqa
            'merge_csv=cardinal_pythonlib.tools.merge_csv:main',
            'remove_duplicate_files=cardinal_pythonlib.tools.remove_duplicate_files:main',  # noqa

            # other
            'rnc_email=cardinal_pythonlib.rnc_email:main',
            'rnc_extract_text=cardinal_pythonlib.rnc_extract_text:main',
        ],
    },
)
