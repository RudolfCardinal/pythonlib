..  cardinal_pythonlib/docs/source/notes_python_package_setup.rst

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


.. _alien: https://wiki.debian.org/Alien
.. _Docker: https://www.docker.com/
.. _gdebi: https://launchpad.net/gdebi
.. _PyCharm: https://www.jetbrains.com/pycharm/


Notes on Python package setup
=============================

Creating Python packages is a little fiddlier than one might hope.


Operating system prerequisites
------------------------------

If your package has non-standard system dependencies, there are a number of
options:

#.  Manual installation by the user.

#.  Packaging your Python code within an OS package, such as:

    - a ``.deb`` file, for Debian Linux, easily installable via gdebi_, e.g.
      ``sudo gdebi DEBFILE``;

    - an ``.rpm`` file, for Red Hat Linux and derivatives, creatable from a
      ``.deb`` file via alien_, and easily installable via ``sudo yum install
      RPMFILE``;

    - Windows packaging.

#.  Docker_

    In general, this is **preferred**, because it guarantees the OS environment
    exactly, is fairly simple to install, and performance remains good.


Python package dependencies: install_requires versus requirements.txt
---------------------------------------------------------------------

Remember
~~~~~~~~

Code in ``setup.py`` needs to cope with (a) installation, as in
``pip install .``, and (b) package creation, as in ``python setup.py sdist``.


Background
~~~~~~~~~~

This is a standard Python problem: "my_package depends on other_package version
1.2.3".

- ``requirements.txt`` is read by "bots" such as Dependabot on Github, so if
  this is your primary list of requirements, automatic pull requests will work.
  It's also read when users do a manual installation from it. And it's read by
  PyCharm_ and other IDEs.

  - But possibly it works without this file? Yes; it should. See below.

- The ``setup(..., install_requires=[...])`` parameter in ``setup.py`` is read
  by ``pip``.

How do these differ? See

- https://packaging.python.org/discussions/install-requires-vs-requirements/
  (not terribly helpful);

- https://stackoverflow.com/questions/6947988/when-to-use-pip-requirements-file-versus-install-requires-in-setup-py

- https://medium.com/knerd/best-practices-for-python-dependency-management-cc8d1913db82

- https://blog.miguelgrinberg.com/post/the-package-dependency-blues

- https://www.b-list.org/weblog/2018/apr/25/lets-talk-about-packages/

- https://www.reddit.com/r/Python/comments/3uzl2a/setuppy_requirementstxt_or_a_combination/

- https://packaging.python.org/en/latest/distributing/#working-in-development-mode

- http://python-packaging-user-guide.readthedocs.org/en/latest/distributing/

- http://jtushman.github.io/blog/2013/06/17/sharing-code-across-applications-with-python/

Note:

- It's better to specify a dependency version range when you are providing
  libraries, and an exact version when you are providing an application.

- When you run a user-defined script from your package, it calls
  ``pkg_resources.load_entry_point(dist, group, name)`` (this is part of
  ``setuptools``). See
  https://setuptools.readthedocs.io/en/latest/pkg_resources.html. This doesn't
  seem to re-call ``setup.py`` or check ``requirements.txt``.

- ``pip`` uses ``install_requires`` and not ``requirements.txt`` when
  installing your package.


Options
~~~~~~~

One "single-source" approach is to define a variable such as
``INSTALL_REQUIRES`` in setup.py that is used in the ``setup(...,
install_requires=INSTALL_REQUIRES)`` and is used to write ``requirements.txt``
(e.g. via an extra call by the developer: ``python setup.py --extras``).

Another is to read and parse ``requirements.txt`` in ``setup.py``.

Experimenting with a package that has a simple requirement for
``semantic_version``:

- No requirements specified: code will crash at runtime with
  ``ModuleNotFoundError: No module named 'semantic_version'``

- ``install_requires`` only:

  - PyCharm notices (even if indirected via a variable).

    But note: it will cope with simple indirection, e.g.

    .. code-block:: python

        REQUIREMENTS = [
            "semantic_version==32.8.4",
        ]
        setup(
            ...,
            install_requires=REQUIREMENTS,
        )

    but not with more complex indirection, e.g.

    .. code-block:: python

        REQUIREMENTS_TEXT = """
            semantic_version==32.8.4
        """
        REQUIREMENTS = []
        with StringIO(REQUIREMENTS_TEXT) as f:
            for line in f.readlines():
                line = line.strip()
                if (not line) or line.startswith('#') or line.startswith('--'):
                    continue
                REQUIREMENTS.append(line)
        setup(
            ...,
            install_requires=REQUIREMENTS,
        )

  - Dependabot is meant to notice. Its code suggests it will cope with
    arbitrary indirection:
    https://github.com/dependabot/dependabot-core/blob/main/python/helpers/lib/parser.py

  - ``pip install`` does what's required and the code runs.

- ``requirements.txt`` only:

  - PyCharm notices.
  - We know Dependabot notices.
  - ``pip install`` does NOT install the necessary dependencies.

  So this option is useless.

The next question is whether ``requirements.txt`` is necessary at all. One
view (e.g. Reddit above) is that it can be kept for development environments,
i.e. the extras required for development but not for running your package.


Conclusion
~~~~~~~~~~

- For package distribution, ``install_requires`` in ``setup.py`` is mandatory,
  and ``requirements.txt`` is optional and therefore perhaps best avoided so
  that automatic code analysis tools don't get confused.


Data and other non-Python files: setup.py versus MANIFEST.in
------------------------------------------------------------

Here's another tricky thing. In ``setup.py``, you have ``package_data`` and
``include_package_data`` arguments to ``setup()``. There is also the file
``MANIFEST.in``.

    #
    # or MANIFEST.in ?
    # - https://stackoverflow.com/questions/24727709/i-dont-understand-python-manifest-in  # noqa: E501
    # - https://stackoverflow.com/questions/1612733/including-non-python-files-with-setup-py  # noqa: E501
    #
    # or both?
    # - https://stackoverflow.com/questions/3596979/manifest-in-ignored-on-python-setup-py-install-no-data-files-installed  # noqa: E501
    # ... MANIFEST gets the files into the distribution
    # ... package_data gets them installed in the distribution
    #
    # data_files is from distutils, and we're using setuptools
    # - https://docs.python.org/3.5/distutils/setupscript.html#installing-additional-files  # noqa: E501



See:

- https://stackoverflow.com/questions/13307408/python-packaging-data-files-are-put-properly-in-tar-gz-file-but-are-not-install

- http://danielsokolowski.blogspot.co.uk/2012/08/setuptools-includepackagedata-option.html

  ... relates to an old problem?

- https://stackoverflow.com/questions/779495/access-data-in-package-subdirectory

- https://packaging.python.org/guides/distributing-packages-using-setuptools/

- https://packaging.python.org/guides/using-manifest-in/#using-manifest-in

- https://setuptools.readthedocs.io/en/latest/userguide/datafiles.html

- https://stackoverflow.com/questions/29036937/how-can-i-include-package-data-without-a-manifest-in-file

- https://stackoverflow.com/questions/24727709/i-dont-understand-python-manifest-in

- https://stackoverflow.com/questions/1612733/including-non-python-files-with-setup-py

  ... relevant

- https://stackoverflow.com/questions/3596979/manifest-in-ignored-on-python-setup-py-install-no-data-files-installed
  ... ``MANIFEST.in`` gets the files into the distribution;
  ... ``package_data`` gets them installed in the distribution

- https://ep2015.europython.eu/media/conference/slides/less-known-packaging-features-and-tricks.pdf

  ... this one is very good.

- http://blog.codekills.net/2011/07/15/lies,-more-lies-and-python-packaging-documentation-on--package_data-/

... the last, in particular, suggesting that both ``MANIFEST.in`` (required for
``sdist``) and ``package_data`` (used for ``install``) are necessary.
However, it seems that you can use just ``MANIFEST.in`` if you specify
``include_package_data=True``.

For complex file specification, you could use Python and then write to
``MANIFEST.in``, but actually the manifest syntax is quite good:

- https://www.reddit.com/r/Python/comments/40s8qw/simplify_your_manifestin_commands/

- https://docs.python.org/3/distutils/commandref.html

So, the two realistic options are:

1.  Have a ``setup.py`` that auto-writes ``MANIFEST.in`` when required.

2.  Specify ``MANIFEST.in`` properly and use ``include_package_data=True``.
    This is probably better. See in particular
    https://ep2015.europython.eu/media/conference/slides/less-known-packaging-features-and-tricks.pdf


Conclusion
~~~~~~~~~~

Use ``MANIFEST.in`` plus ``setup(..., include_package_data=True)``.
Use the full syntax available for ``MANIFEST.in``.

To find all extensions (for the ``global-exclude`` command), use:

    .. code-block:: bash

        find . -type f | perl -ne 'print $1 if m/\.([^.\/]+)$/' | sort -u


Beware a nasty caching effect
-----------------------------

Consider deleting any old ``MY_PACKAGE_NAME.egg_info`` directory from within
``setup.py``, **before** calling ``setup()``. This may be particularly
applicable for packages that ship "data". See
http://blog.codekills.net/2011/07/15/lies,-more-lies-and-python-packaging-documentation-on--package_data-/

Like this, for example:

.. code-block:: python

    # setup.py

    import os
    import shutil

    PACKAGE_NAME = "MY_PACKAGE_NAME"
    THIS_DIR = os.path.abspath(os.path.dirname(__file__))  # contains setup.py
    EGG_DIR = os.path.join(THIS_DIR, PACKAGE_NAME + ".egg-info")

    shutil.rmtree(EGG_DIR, ignore_errors=True)

    setup(...)

This is perhaps meant to be unnecessary, per
https://stackoverflow.com/questions/3779915/why-does-python-setup-py-sdist-create-unwanted-project-egg-info-in-project-r,
but maybe isn't.

It appears to be unnecessary once you shift to ``MANIFEST.in`` and
``include_package_data=True``.
