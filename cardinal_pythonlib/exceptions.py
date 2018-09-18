#!/usr/bin/env python
# cardinal_pythonlib/exceptions.py

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

**Functions for exception handling.**

"""

import logging
import sys
import traceback
from typing import Dict

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Exception handling
# =============================================================================

def add_info_to_exception(err: Exception, info: Dict) -> None:
    """
    Adds an information dictionary to an exception.
    
    See
    http://stackoverflow.com/questions/9157210/how-do-i-raise-the-same-exception-with-a-custom-message-in-python
    
    Args:
        err: the exception to be modified
        info: the information to add
    """  # noqa
    if not err.args:
        err.args = ('', )
    err.args += (info, )


def recover_info_from_exception(err: Exception) -> Dict:
    """
    Retrives the information added to an exception by
    :func:`add_info_to_exception`.
    """
    if len(err.args) < 1:
        return {}
    info = err.args[-1]
    if not isinstance(info, dict):
        return {}
    return info


def die(exc: Exception = None, exit_code: int = 1) -> None:
    """
    It is not clear that Python guarantees to exit with a non-zero exit code
    (errorlevel in DOS/Windows) upon an unhandled exception. So this function
    produces the usual stack trace then dies with the specified exit code.

    See
    http://stackoverflow.com/questions/9555133/e-printstacktrace-equivalent-in-python.

    Test code:
    
    .. code-block:: python

        import logging
        import sys
        import traceback
        logging.basicConfig(level=logging.DEBUG)
        log = logging.getLogger()
        
        def fail():
            try:
                x = 1/0
            except Exception as exc:
                die(exc)

    Then call
    
    .. code-block:: python
    
        fail()
        
    ... which should exit Python; then from Linux (for example):
    
    .. code-block:: bash
    
        echo $?  # show exit code

    """  # noqa
    if exc:
        lines = traceback.format_exception(
            None,  # etype: ignored
            exc,
            exc.__traceback__)  # https://www.python.org/dev/peps/pep-3134/
        msg = "".join(lines)
        # Method 1:
        # print("".join(lines), file=sys.stderr, flush=True)
        # Method 2:
        log.critical(msg)
    log.critical("Exiting with exit code {}".format(exit_code))
    sys.exit(exit_code)
