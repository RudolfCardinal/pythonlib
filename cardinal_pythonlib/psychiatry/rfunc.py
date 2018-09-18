#!/usr/bin/env python
# cardinal_pythonlib/psychiatry/rfunc.py

"""
===============================================================================

    Original code copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**WORK IN PROGRESS. Doesn't do much that's useful at present.**

Functions to be used from R via reticulate
(https://cran.r-project.org/web/packages/reticulate/index.html).

See ``drugs.py`` for notes on how to get reticulate talking to this library.

Briefly:

.. code-block:: r

    # -------------------------------------------------------------------------
    # Load libraries
    # -------------------------------------------------------------------------

    library(data.table)
    library(reticulate)

    # -------------------------------------------------------------------------
    # Set up reticulate
    # -------------------------------------------------------------------------

    VENV <- "~/dev/venvs/cardinal_pythonlib"  # or your preferred virtualenv
    PYTHON_EXECUTABLE <- ifelse(
        .Platform$OS.type == "windows",
        file.path(VENV, "Scripts", "python.exe"),  # Windows
        file.path(VENV, "bin", "python")  # Linux
    )
    reticulate::use_python(PYTHON_EXECUTABLE, required=TRUE)

    # -------------------------------------------------------------------------
    # Import Python modules
    # -------------------------------------------------------------------------

    cpl_rfunc <- reticulate::import("cardinal_pythonlib.psychiatry.rfunc")

    # -------------------------------------------------------------------------
    # Try other things
    # -------------------------------------------------------------------------
    
    repl_python()  # start an interactive Python session

"""  # noqa

import sys
from typing import Any, Dict


# =============================================================================
# Simple information for R
# =============================================================================

def get_python_repr(x: Any) -> str:
    r"""
    A few notes:
    
    **data.table()**
    
    Data tables are converted to a Python dictionary:
    
    .. code-block:: r

        dt <- data.table(
            subject = c("Alice", "Bob", "Charles", "Dawn", "Egbert", "Flora"),
            drug = c("citalopram", "Cipramil", "Prozac", "fluoxetine",
                     "Priadel", "Haldol")
        )
        dt_repr <- cpl_rfunc$get_python_repr(dt)

    gives this when a duff import is used via
    ``reticulate::import_from_path()``:

    .. code-block:: none

        [1] "{'drug': ['citalopram', 'Cipramil', 'Prozac', 'fluoxetine',
        'Priadel', 'Haldol'], 'subject': ['Alice', 'Bob', 'Charles', 'Dawn',
        'Egbert', 'Flora']}"

    but this when a proper import is used via ``reticulate::import()``:

    .. code-block:: none

        [1] "   subject        drug\n0    Alice  citalopram\n1      Bob
        Cipramil\n2  Charles      Prozac\n3     Dawn  fluoxetine\n4   Egbert
         Priadel\n5    Flora      Haldol"

    """
    return repr(x)


def get_python_repr_of_type(x: Any) -> str:
    """
    See ``get_python_repr``.

    .. code-block:: r

        dt_type_repr <- cpl_rfunc$get_python_repr_of_type(dt)

    gives this when a duff import is used via
    ``reticulate::import_from_path()``:

    .. code-block:: none

        [1] "<class 'dict'>"

    but this when a proper import is used via ``reticulate::import()``:

    .. code-block:: none

        [1] "<class 'pandas.core.frame.DataFrame'>"

    The same is true of a data.frame().

    """
    return repr(type(x))


def test_get_dict() -> Dict[str, Any]:
    """
    Test with:

    .. code-block:: r

        testdict <- cpl_rfunc$test_get_dict()

    This gives a list:

    .. code-block:: none

        > testdict
        $strings
        [1] "one"   "two"   "three" "four"  "five"

        $integers
        [1] 1 2 3 4 5

        $floats
        [1] 1.1 2.1 3.1 4.1 5.1

    """
    return {
        'integers': [1, 2, 3, 4, 5],
        'floats': [1.1, 2.1, 3.1, 4.1, 5.1],
        'strings': ["one", "two", "three", "four", "five"],
    }


def flush_stdout_stderr() -> None:
    """
    R code won't see much unless we flush stdout/stderr manually.
    See also https://github.com/rstudio/reticulate/issues/284
    """
    sys.stdout.flush()
    sys.stderr.flush()
