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

from setuptools import setup
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
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache Software License',

        'Natural Language :: English',

        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',

        'Topic :: Software Development :: Libraries',
    ],

    keywords='cardinal',

    packages=['cardinal_pythonlib'],

    install_requires=[
        'six',  # Python 2/3 compatibility
    ],

    entry_points={
        'console_scripts': [
            # Format is 'script=module:function".
            'rnc_email=cardinal_pythonlib.rnc_email:main',
            'rnc_extract_text=cardinal_pythonlib.rnc_extract_text:main',
        ],
    },
)
