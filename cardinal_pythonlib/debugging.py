#!/usr/bin/env python
# cardinal_pythonlib/debugging.py

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

**Functions for debugging.**

"""

import ctypes
import inspect
from inspect import FrameInfo
import logging
import pdb
import sys
import traceback
from types import FrameType
from typing import Any, Callable, List, Optional

log = logging.getLogger(__name__)  # don't use BraceStyleAdapter; {} used
log.addHandler(logging.NullHandler())


# =============================================================================
# Debugging
# =============================================================================

def pdb_run(func: Callable, *args: Any, **kwargs: Any) -> None:
    """
    Calls ``func(*args, **kwargs)``; if it raises an exception, break into
    the ``pdb`` debugger.
    """
    # noinspection PyBroadException
    try:
        func(*args, **kwargs)
    except:  # nopep8
        type_, value, tb = sys.exc_info()
        traceback.print_exc()
        pdb.post_mortem(tb)


def cause_segfault() -> None:
    """
    This function will induce a segmentation fault and CRASH the application.
    Method as per https://docs.python.org/3/library/faulthandler.html
    """
    ctypes.string_at(0)  # will crash!


# =============================================================================
# Name of calling class/function, for status messages
# =============================================================================

def get_class_name_from_frame(fr: FrameType) -> Optional[str]:
    """
    A frame contains information about a specific call in the Python call
    stack; see https://docs.python.org/3/library/inspect.html.

    If the call was to a member function of a class, this function attempts
    to read the class's name. It returns ``None`` otherwise.
    """
    # http://stackoverflow.com/questions/2203424/python-how-to-retrieve-class-information-from-a-frame-object  # noqa
    args, _, _, value_dict = inspect.getargvalues(fr)
    # we check the first parameter for the frame function is named 'self'
    if len(args) and args[0] == 'self':
        # in that case, 'self' will be referenced in value_dict
        instance = value_dict.get('self', None)
        if instance:
            # return its class
            cls = getattr(instance, '__class__', None)
            if cls:
                return cls.__name__
            return None
    # return None otherwise
    return None


def get_caller_name(back: int = 0) -> str:
    """
    Return details about the CALLER OF THE CALLER (plus n calls further back)
    of this function.

    So, if your function calls :func:`get_caller_name`, it will return the
    name of the function that called your function! (Or ``back`` calls further
    back.)

    Example:

    .. code-block:: python

        from cardinal_pythonlib.debugging import get_caller_name

        def who_am_i():
            return get_caller_name()

        class MyClass(object):
            def classfunc(self):
                print("I am: " + who_am_i())
                print("I was called by: " + get_caller_name())
                print("That was called by: " + get_caller_name(back=1))

        def f2():
            x = MyClass()
            x.classfunc()

        def f1():
            f2()

        f1()

    will produce:

    .. code-block:: none

        I am: MyClass.classfunc
        I was called by: f2
        That was called by: f1

    """
    # http://stackoverflow.com/questions/5067604/determine-function-name-from-within-that-function-without-using-traceback  # noqa
    try:
        # noinspection PyProtectedMember
        frame = sys._getframe(back + 2)
    except ValueError:
        # Stack isn't deep enough.
        return '?'
    function_name = frame.f_code.co_name
    class_name = get_class_name_from_frame(frame)
    if class_name:
        return "{}.{}".format(class_name, function_name)
    return function_name


# =============================================================================
# Who called us?
# =============================================================================

def get_caller_stack_info(start_back: int = 1) -> List[str]:
    r"""
    Retrieves a textual representation of the call stack.

    Args:
        start_back: number of calls back in the frame stack (starting
            from the frame stack as seen by :func:`get_caller_stack_info`)
            to begin with

    Returns:
        list of descriptions

    Example:

    .. code-block:: python

        from cardinal_pythonlib.debugging import get_caller_stack_info

        def who_am_i():
            return get_caller_name()

        class MyClass(object):
            def classfunc(self):
                print("Stack info:\n" + "\n".join(get_caller_stack_info()))

        def f2():
            x = MyClass()
            x.classfunc()

        def f1():
            f2()

        f1()

    if called from the Python prompt will produce:

    .. code-block:: none

        Stack info:
        <module>()
        ... defined at <stdin>:1
        ... line 1 calls next in stack; code is:

        f1()
        ... defined at <stdin>:1
        ... line 2 calls next in stack; code is:

        f2()
        ... defined at <stdin>:1
        ... line 3 calls next in stack; code is:

        classfunc(self=<__main__.MyClass object at 0x7f86a009c6d8>)
        ... defined at <stdin>:2
        ... line 3 calls next in stack; code is:

    and if called from a Python file will produce:

    .. code-block:: none

        Stack info:
        <module>()
        ... defined at /home/rudolf/tmp/stack.py:1
        ... line 17 calls next in stack; code is:
        f1()

        f1()
        ... defined at /home/rudolf/tmp/stack.py:14
        ... line 15 calls next in stack; code is:
            f2()

        f2()
        ... defined at /home/rudolf/tmp/stack.py:10
        ... line 12 calls next in stack; code is:
            x.classfunc()

        classfunc(self=<__main__.MyClass object at 0x7fd7a731f358>)
        ... defined at /home/rudolf/tmp/stack.py:7
        ... line 8 calls next in stack; code is:
                print("Stack info:\n" + "\n".join(get_caller_stack_info()))

    """
    # "0 back" is debug_callers, so "1 back" its caller
    # https://docs.python.org/3/library/inspect.html
    callers = []  # type: List[str]
    frameinfolist = inspect.stack()  # type: List[FrameInfo]  # noqa
    frameinfolist = frameinfolist[start_back:]
    for frameinfo in frameinfolist:
        frame = frameinfo.frame
        function_defined_at = "... defined at {filename}:{line}".format(
            filename=frame.f_code.co_filename,
            line=frame.f_code.co_firstlineno,
        )
        argvalues = inspect.getargvalues(frame)
        formatted_argvalues = inspect.formatargvalues(*argvalues)
        function_call = "{funcname}{argvals}".format(
            funcname=frame.f_code.co_name,
            argvals=formatted_argvalues,
        )
        code_context = frameinfo.code_context
        code = "".join(code_context) if code_context else ""
        onwards = "... line {line} calls next in stack; code is:\n{c}".format(
            line=frame.f_lineno,
            c=code,
        )
        description = "\n".join([function_call, function_defined_at, onwards])
        callers.append(description)
    return list(reversed(callers))


# =============================================================================
# Show the structure of an object in detail
# =============================================================================

def debug_object(obj, log_level: int = logging.DEBUG) -> None:
    """
    Sends details about a Python to the log, specifically its ``repr()``
    representation, and all of its attributes with their name, value, and type.

    Args:
        obj: object to debug
        log_level: log level to use; default is ``logging.DEBUG``
    """
    msgs = ["For {o!r}:".format(o=obj)]
    for attrname in dir(obj):
        attribute = getattr(obj, attrname)
        msgs.append("- {an!r}: {at!r}, of type {t!r}".format(
            an=attrname, at=attribute, t=type(attribute)))
    log.log(log_level, "\n".join(msgs))
