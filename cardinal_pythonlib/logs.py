#!/usr/bin/env python
# cardinal_pythonlib/logs.py

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

**Support functions for logging.**

See https://docs.python.org/3.4/howto/logging.html#library-config

USER CODE should use the following general methods.

(a) Simple:

    .. code-block:: python

        import logging
        log = logging.getLogger(__name__)  # for your own logs
        logging.basicConfig()

(b) More complex:

    .. code-block:: python

        import logging
        log = logging.getLogger(__name__)
        logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATEFMT,
                            level=loglevel)

(c) Using colour conveniently:

    .. code-block:: python

        import logging
        mylogger = logging.getLogger(__name__)
        rootlogger = logging.getLogger()

        from whisker.log import configure_logger_for_colour
        configure_logger_for_colour(rootlogger)


LIBRARY CODE should use the following general methods.

.. code-block:: python

    import logging
    log = logging.getLogger(__name__)

    # ... and if you want to suppress output unless the user configures logs:
    log.addHandler(logging.NullHandler())
    # ... which only needs to be done in the __init__.py for the package
    #     http://stackoverflow.com/questions/12296214

    # LIBRARY CODE SHOULD NOT ADD ANY OTHER HANDLERS; see above.

DO NOT call this module "logging"! Many things may get confused.

"""

from html import escape
from inspect import Parameter, signature
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, TextIO, Tuple, Union

from colorlog import ColoredFormatter

# =============================================================================
# Quick configuration of a specific log format
# =============================================================================

LOG_FORMAT = '%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:%(message)s'
LOG_FORMAT_WITH_PID = (
    '%(asctime)s.%(msecs)03d:%(levelname)s:{}:%(name)s:%(message)s'.format(
        os.getpid()))

LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'

LOG_COLORS = {'DEBUG': 'cyan',
              'INFO': 'green',
              'WARNING': 'bold_yellow',
              'ERROR': 'bold_red',
              'CRITICAL': 'bold_white,bg_red'}


def get_monochrome_handler(
        extranames: List[str] = None,
        with_process_id: bool = False,
        with_thread_id: bool = False,
        stream: TextIO = None) -> logging.StreamHandler:
    """
    Gets a monochrome log handler using a standard format.

    Args:
        extranames: additional names to append to the logger's name
        with_process_id: include the process ID in the logger's name?
        with_thread_id: include the thread ID in the logger's name?
        stream: ``TextIO`` stream to send log output to

    Returns:
        the :class:`logging.StreamHandler`

    """
    fmt = "%(asctime)s.%(msecs)03d"
    if with_process_id or with_thread_id:
        procinfo = []  # type: List[str]
        if with_process_id:
            procinfo.append("p%(process)d")
        if with_thread_id:
            procinfo.append("t%(thread)d")
        fmt += " [{}]".format(".".join(procinfo))
    extras = ":" + ":".join(extranames) if extranames else ""
    fmt += " %(name)s{extras}:%(levelname)s: ".format(extras=extras)
    fmt += "%(message)s"
    f = logging.Formatter(fmt, datefmt=LOG_DATEFMT, style='%')
    h = logging.StreamHandler(stream)
    h.setFormatter(f)
    return h


def get_colour_handler(extranames: List[str] = None,
                       with_process_id: bool = False,
                       with_thread_id: bool = False,
                       stream: TextIO = None) -> logging.StreamHandler:
    """
    Gets a colour log handler using a standard format.

    Args:
        extranames: additional names to append to the logger's name
        with_process_id: include the process ID in the logger's name?
        with_thread_id: include the thread ID in the logger's name?
        stream: ``TextIO`` stream to send log output to

    Returns:
        the :class:`logging.StreamHandler`

    """
    fmt = "%(white)s%(asctime)s.%(msecs)03d"  # this is dim white = grey
    if with_process_id or with_thread_id:
        procinfo = []  # type: List[str]
        if with_process_id:
            procinfo.append("p%(process)d")
        if with_thread_id:
            procinfo.append("t%(thread)d")
        fmt += " [{}]".format(".".join(procinfo))
    extras = ":" + ":".join(extranames) if extranames else ""
    fmt += " %(name)s{extras}:%(levelname)s: ".format(extras=extras)
    fmt += "%(reset)s%(log_color)s%(message)s"
    cf = ColoredFormatter(fmt,
                          datefmt=LOG_DATEFMT,
                          reset=True,
                          log_colors=LOG_COLORS,
                          secondary_log_colors={},
                          style='%')
    ch = logging.StreamHandler(stream)
    ch.setFormatter(cf)
    return ch


def configure_logger_for_colour(logger: logging.Logger,
                                level: int = logging.INFO,
                                remove_existing: bool = False,
                                extranames: List[str] = None,
                                with_process_id: bool = False,
                                with_thread_id: bool = False) -> None:
    """
    Applies a preconfigured datetime/colour scheme to a logger.

    Should ONLY be called from the ``if __name__ == 'main'`` script;
    see https://docs.python.org/3.4/howto/logging.html#library-config.

    Args:
        logger: logger to modify
        level: log level to set
        remove_existing: remove existing handlers from logger first?
        extranames: additional names to append to the logger's name
        with_process_id: include the process ID in the logger's name?
        with_thread_id: include the thread ID in the logger's name?
    """
    if remove_existing:
        logger.handlers = []  # http://stackoverflow.com/questions/7484454
    handler = get_colour_handler(extranames,
                                 with_process_id=with_process_id,
                                 with_thread_id=with_thread_id)
    handler.setLevel(level)
    logger.addHandler(handler)
    logger.setLevel(level)


def main_only_quicksetup_rootlogger(level: int = logging.DEBUG,
                                    with_process_id: bool = False,
                                    with_thread_id: bool = False) -> None:
    """
    Quick function to set up the root logger for colour.

    Should ONLY be called from the ``if __name__ == 'main'`` script;
    see https://docs.python.org/3.4/howto/logging.html#library-config.

    Args:
        level: log level to set
        with_process_id: include the process ID in the logger's name?
        with_thread_id: include the thread ID in the logger's name?
    """
    # Nasty. Only call from "if __name__ == '__main__'" clauses!
    rootlogger = logging.getLogger()
    configure_logger_for_colour(rootlogger, level, remove_existing=True,
                                with_process_id=with_process_id,
                                with_thread_id=with_thread_id)
    # logging.basicConfig(level=level)


# =============================================================================
# Generic log functions
# =============================================================================

def remove_all_logger_handlers(logger: logging.Logger) -> None:
    """
    Remove all handlers from a logger.

    Args:
        logger: logger to modify
    """
    while logger.handlers:
        h = logger.handlers[0]
        logger.removeHandler(h)


def reset_logformat(logger: logging.Logger,
                    fmt: str,
                    datefmt: str = '%Y-%m-%d %H:%M:%S') -> None:
    """
    Create a new formatter and apply it to the logger.

    :func:`logging.basicConfig` won't reset the formatter if another module
    has called it, so always set the formatter like this.

    Args:
        logger: logger to modify
        fmt: passed to the ``fmt=`` argument of :class:`logging.Formatter`
        datefmt: passed to the ``datefmt=`` argument of
            :class:`logging.Formatter`
    """
    handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    handler.setFormatter(formatter)
    remove_all_logger_handlers(logger)
    logger.addHandler(handler)
    logger.propagate = False


def reset_logformat_timestamped(logger: logging.Logger,
                                extraname: str = "",
                                level: int = logging.INFO) -> None:
    """
    Apply a simple time-stamped log format to an existing logger, and set
    its loglevel to either ``logging.DEBUG`` or ``logging.INFO``.

    Args:
        logger: logger to modify
        extraname: additional name to append to the logger's name
        level: log level to set
    """
    namebit = extraname + ":" if extraname else ""
    fmt = ("%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:" + namebit +
           "%(message)s")
    # logger.info(fmt)
    reset_logformat(logger, fmt=fmt)
    # logger.info(fmt)
    logger.setLevel(level)


# =============================================================================
# Helper functions
# =============================================================================

def configure_all_loggers_for_colour(remove_existing: bool = True) -> None:
    """
    Applies a preconfigured datetime/colour scheme to ALL logger.

    Should ONLY be called from the ``if __name__ == 'main'`` script;
    see https://docs.python.org/3.4/howto/logging.html#library-config.

    Generally MORE SENSIBLE just to apply a handler to the root logger.

    Args:
        remove_existing: remove existing handlers from logger first?

    """
    handler = get_colour_handler()
    apply_handler_to_all_logs(handler, remove_existing=remove_existing)


def apply_handler_to_root_log(handler: logging.Handler,
                              remove_existing: bool = False) -> None:
    """
    Applies a handler to all logs, optionally removing existing handlers.

    Should ONLY be called from the ``if __name__ == 'main'`` script;
    see https://docs.python.org/3.4/howto/logging.html#library-config.

    Generally MORE SENSIBLE just to apply a handler to the root logger.

    Args:
        handler: the handler to apply
        remove_existing: remove existing handlers from logger first?
    """
    rootlog = logging.getLogger()
    if remove_existing:
        rootlog.handlers = []
    rootlog.addHandler(handler)


def apply_handler_to_all_logs(handler: logging.Handler,
                              remove_existing: bool = False) -> None:
    """
    Applies a handler to all logs, optionally removing existing handlers.

    Should ONLY be called from the ``if __name__ == 'main'`` script;
    see https://docs.python.org/3.4/howto/logging.html#library-config.

    Generally MORE SENSIBLE just to apply a handler to the root logger.

    Args:
        handler: the handler to apply
        remove_existing: remove existing handlers from logger first?
    """
    # noinspection PyUnresolvedReferences
    for name, obj in logging.Logger.manager.loggerDict.items():
        if remove_existing:
            obj.handlers = []  # http://stackoverflow.com/questions/7484454
        obj.addHandler(handler)


def copy_root_log_to_file(filename: str,
                          fmt: str = LOG_FORMAT,
                          datefmt: str = LOG_DATEFMT) -> None:
    """
    Copy all currently configured logs to the specified file.

    Should ONLY be called from the ``if __name__ == 'main'`` script;
    see https://docs.python.org/3.4/howto/logging.html#library-config.
    """
    fh = logging.FileHandler(filename)
    # default file mode is 'a' for append
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    fh.setFormatter(formatter)
    apply_handler_to_root_log(fh)


def copy_all_logs_to_file(filename: str,
                          fmt: str = LOG_FORMAT,
                          datefmt: str = LOG_DATEFMT) -> None:
    """
    Copy all currently configured logs to the specified file.

    Should ONLY be called from the ``if __name__ == 'main'`` script;
    see https://docs.python.org/3.4/howto/logging.html#library-config.

    Args:
        filename: file to send log output to
        fmt: passed to the ``fmt=`` argument of :class:`logging.Formatter`
        datefmt: passed to the ``datefmt=`` argument of
            :class:`logging.Formatter`
    """
    fh = logging.FileHandler(filename)
    # default file mode is 'a' for append
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    fh.setFormatter(formatter)
    apply_handler_to_all_logs(fh)


# noinspection PyProtectedMember
def get_formatter_report(f: logging.Formatter) -> Optional[Dict[str, str]]:
    """
    Returns information on a log formatter, as a dictionary.
    For debugging.
    """
    if f is None:
        return None
    return {
        '_fmt': f._fmt,
        'datefmt': f.datefmt,
        '_style': str(f._style),
    }


def get_handler_report(h: logging.Handler) -> Dict[str, Any]:
    """
    Returns information on a log handler, as a dictionary.
    For debugging.
    """
    return {
        'get_name()': h.get_name(),
        'level': h.level,
        'formatter': get_formatter_report(h.formatter),
        'filters': h.filters,
    }


def get_log_report(log: Union[logging.Logger,
                              logging.PlaceHolder]) -> Dict[str, Any]:
    """
    Returns information on a log, as a dictionary. For debugging.
    """
    if isinstance(log, logging.Logger):
        # suppress invalid error for Logger.manager:
        # noinspection PyUnresolvedReferences
        return {
            '(object)': str(log),
            'level': log.level,
            'disabled': log.disabled,
            'propagate': log.propagate,
            'parent': str(log.parent),
            'manager': str(log.manager),
            'handlers': [get_handler_report(h) for h in log.handlers],
        }
    elif isinstance(log, logging.PlaceHolder):
        return {
            "(object)": str(log),
        }
    else:
        raise ValueError("Unknown object type: {!r}".format(log))


def print_report_on_all_logs() -> None:
    """
    Use :func:`print` to report information on all logs.
    """
    d = {}
    # noinspection PyUnresolvedReferences
    for name, obj in logging.Logger.manager.loggerDict.items():
        d[name] = get_log_report(obj)
    rootlogger = logging.getLogger()
    d['(root logger)'] = get_log_report(rootlogger)
    print(json.dumps(d, sort_keys=True, indent=4, separators=(',', ': ')))


def set_level_for_logger_and_its_handlers(log: logging.Logger,
                                          level: int) -> None:
    """
    Set a log level for a log and all its handlers.

    Args:
        log: log to modify
        level: log level to set
    """
    log.setLevel(level)
    for h in log.handlers:  # type: logging.Handler
        h.setLevel(level)


# =============================================================================
# HTML formatter
# =============================================================================

class HtmlColorFormatter(logging.Formatter):
    """
    Class to format Python logs in coloured HTML.
    """
    log_colors = {
        logging.DEBUG: '#008B8B',  # dark cyan
        logging.INFO: '#00FF00',  # green
        logging.WARNING: '#FFFF00',  # yellow
        logging.ERROR: '#FF0000',  # red
        logging.CRITICAL: '#FF0000',  # red
    }
    log_background_colors = {
        logging.DEBUG: None,
        logging.INFO: None,
        logging.WARNING: None,
        logging.ERROR: None,
        logging.CRITICAL: '#FFFFFF',  # white
    }

    def __init__(self, append_br: bool = False,
                 replace_nl_with_br: bool = True) -> None:
        r"""
        Args:
            append_br: append ``<br>`` to each line?
            replace_nl_with_br: replace ``\n`` with ``<br>`` in messages?

        See https://hg.python.org/cpython/file/3.5/Lib/logging/__init__.py
        """
        super().__init__(
            fmt='%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            style='%'
        )
        self.append_br = append_br
        self.replace_nl_with_br = replace_nl_with_br

    def format(self, record: logging.LogRecord) -> str:
        """
        Internal function to format the :class:`LogRecord` as HTML.

        See https://docs.python.org/3.4/library/logging.html#logging.LogRecord
        """

        # message = super().format(record)
        super().format(record)
        # Since fmt does not contain asctime, the Formatter.format()
        # will not write asctime (since its usesTime()) function will be
        # false. Therefore:
        record.asctime = self.formatTime(record, self.datefmt)
        bg_col = self.log_background_colors[record.levelno]
        msg = escape(record.getMessage())
        # escape() won't replace \n but will replace & etc.
        if self.replace_nl_with_br:
            msg = msg.replace("\n", "<br>")
        html = (
            '<span style="color:#008B8B">{time}.{ms:03d} {name}:{lvname}: '
            '</span><span style="color:{color}{bg}">{msg}</font>{br}'.format(
                time=record.asctime,
                ms=int(record.msecs),
                name=record.name,
                lvname=record.levelname,
                color=self.log_colors[record.levelno],
                msg=msg,
                bg=";background-color:{}".format(bg_col) if bg_col else "",
                br="<br>" if self.append_br else "",
            )
        )
        # print("record.__dict__: {}".format(record.__dict__))
        # print("html: {}".format(html))
        return html


# =============================================================================
# HtmlColorHandler
# =============================================================================

class HtmlColorHandler(logging.StreamHandler):
    """
    HTML handler (using :class:`HtmlColorFormatter`) that sends output to a
    function, e.g. for display in a Qt window
    """
    def __init__(self, logfunction: Callable[[str], None],
                 level: int = logging.INFO) -> None:
        super().__init__()
        self.logfunction = logfunction
        self.setFormatter(HtmlColorFormatter())
        self.setLevel(level)

    def emit(self, record: logging.LogRecord) -> None:
        """
        Internal function to process a :class:`LogRecord`.
        """
        # noinspection PyBroadException
        try:
            html = self.format(record)
            self.logfunction(html)
        except:  # nopep8
            self.handleError(record)


# =============================================================================
# Brace formatters, for log.info("{}, {}", "hello", "world")
# =============================================================================

# - https://docs.python.org/3/howto/logging-cookbook.html#use-of-alternative-formatting-styles  # noqa
# - https://stackoverflow.com/questions/13131400/logging-variable-data-with-new-format-string  # noqa
# - https://stackoverflow.com/questions/13131400/logging-variable-data-with-new-format-string/24683360#24683360  # noqa
# ... plus modifications to use inspect.signature() not inspect.getargspec()
# ... plus a performance tweak so we're not calling signature() every time
# See also:
# - https://www.simonmweber.com/2014/11/24/python-logging-traps.html

class BraceMessage(object):
    """
    Class to represent a message that includes a message including braces
    (``{}``) and a set of ``args``/``kwargs``. When converted to a ``str``,
    the message is realized via ``msg.format(*args, **kwargs)``.
    """
    def __init__(self,
                 fmt: str,
                 args: Tuple[Any, ...],
                 kwargs: Dict[str, Any]) -> None:
        # This version uses args and kwargs, not *args and **kwargs, for
        # performance reasons:
        # https://stackoverflow.com/questions/31992424/performance-implications-of-unpacking-dictionaries-in-python  # noqa
        # ... and since we control creation entirely, we may as well go fast
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs
        # print("Creating BraceMessage with: fmt={}, args={}, "
        #       "kwargs={}".format(repr(fmt), repr(args), repr(kwargs)))

    def __str__(self) -> str:
        return self.fmt.format(*self.args, **self.kwargs)


class BraceStyleAdapter(logging.LoggerAdapter):
    def __init__(self,
                 logger: logging.Logger,
                 pass_special_logger_args: bool = True,
                 strip_special_logger_args_from_fmt: bool = False) -> None:
        """
        Wraps a logger so we can use ``{}``-style string formatting.

        Args:
            logger:
                a logger
            pass_special_logger_args:
                should we continue to pass any special arguments to the logger
                itself? True is standard; False probably brings a slight
                performance benefit, but prevents log.exception() from working
                properly, as the 'exc_info' parameter will be stripped.
            strip_special_logger_args_from_fmt:
                If we're passing special arguments to the logger, should we
                remove them from the argments passed to the string formatter?
                There is no obvious cost to saying no.
                
        Specimen use:
        
        .. code-block:: python
        
            import logging
            from cardinal_pythonlib.logs import BraceStyleAdapter, main_only_quicksetup_rootlogger 
            
            log = BraceStyleAdapter(logging.getLogger(__name__))
            
            main_only_quicksetup_rootlogger(level=logging.DEBUG)
            
            log.info("Hello {}, {title} {surname}!", "world", title="Mr", surname="Smith") 
            # 2018-09-17 16:13:50.404 __main__:INFO: Hello world, Mr Smith!
        
        """  # noqa
        super().__init__(logger=logger, extra=None)
        self.pass_special_logger_args = pass_special_logger_args
        self.strip_special_logger_args_from_fmt = strip_special_logger_args_from_fmt  # noqa
        # getargspec() returns:
        #   named tuple: ArgSpec(args, varargs, keywords, defaults)
        #   ... args = list of parameter names
        #   ... varargs = names of the * parameters, or None
        #   ... keywords = names of the ** parameters, or None
        #   ... defaults = tuple of default argument values, or None
        # signature() returns a Signature object:
        #   ... parameters: ordered mapping of name -> Parameter
        #   ... ... https://docs.python.org/3/library/inspect.html#inspect.Parameter  # noqa
        # Direct equivalence:
        #   https://github.com/praw-dev/praw/issues/541
        # So, old:
        # logargnames = getargspec(self.logger._log).args[1:]
        # and new:
        # noinspection PyProtectedMember
        sig = signature(self.logger._log)
        self.logargnames = [p.name for p in sig.parameters.values()
                            if p.kind == Parameter.POSITIONAL_OR_KEYWORD]
        # e.g.: ['level', 'msg', 'args', 'exc_info', 'extra', 'stack_info']
        # print("self.logargnames: " + repr(self.logargnames))

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(level):
            # print("log: msg={}, args={}, kwargs={}".format(
            #     repr(msg), repr(args), repr(kwargs)))
            if self.pass_special_logger_args:
                msg, log_kwargs = self.process(msg, kwargs)
                # print("... log: msg={}, log_kwargs={}".format(
                #     repr(msg), repr(log_kwargs)))
            else:
                log_kwargs = {}
            # noinspection PyProtectedMember
            self.logger._log(level, BraceMessage(msg, args, kwargs), (),
                             **log_kwargs)

    def process(self, msg: str,
                kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        special_param_names = [k for k in kwargs.keys()
                               if k in self.logargnames]
        log_kwargs = {k: kwargs[k] for k in special_param_names}
        # ... also: remove them from the starting kwargs?
        if self.strip_special_logger_args_from_fmt:
            for k in special_param_names:
                kwargs.pop(k)
        return msg, log_kwargs


# =============================================================================
# Testing
# =============================================================================

if __name__ == '__main__':
    """
    Command-line validation checks.
    """
    main_only_quicksetup_rootlogger(logging.INFO)
    _log = BraceStyleAdapter(logging.getLogger(__name__))
    _log.info("1. Hello!")
    _log.info("1. Hello, {}!", "world")
    _log.info("1. Hello, foo={foo}, bar={bar}!", foo="foo", bar="bar")
    _log.info("1. Hello, {}; foo={foo}, bar={bar}!", "world", foo="foo",
              bar="bar")
    _log.info("1. Hello, {}; foo={foo}, bar={bar}!", "world", foo="foo",
              bar="bar", extra={'somekey': 'somevalue'})
