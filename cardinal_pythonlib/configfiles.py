#!/usr/bin/env python
# cardinal_pythonlib/configfiles.py

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

**Support functions for config (.INI) file reading.**

"""

from configparser import ConfigParser, NoOptionError
import logging
from typing import Any, Callable, Iterable, List

from .logs import BraceStyleAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


# =============================================================================
# Style 1
# =============================================================================

def get_config_string_option(parser: ConfigParser,
                             section: str,
                             option: str,
                             default: str = None) -> str:
    """
    Retrieves a string value from a parser.

    Args:
        parser: instance of :class:`ConfigParser`
        section: section name within config file
        option: option (variable) name within that section
        default: value to return if option is absent

    Returns:
        string value

    Raises:
        ValueError: if the section is absent

    """
    if not parser.has_section(section):
        raise ValueError("config missing section: " + section)
    return parser.get(section, option, fallback=default)


def read_config_string_options(obj: Any,
                               parser: ConfigParser,
                               section: str,
                               options: Iterable[str],
                               default: str = None) -> None:
    """
    Reads config options and writes them as attributes of ``obj``, with
    attribute names as per ``options``.

    Args:
        obj: the object to modify
        parser: instance of :class:`ConfigParser`
        section: section name within config file
        options: option (variable) names within that section
        default: value to use for any missing options

    Returns:

    """
    # enforce_str removed; ConfigParser always returns strings unless asked
    # specifically
    for o in options:
        setattr(obj, o, get_config_string_option(parser, section, o,
                                                 default=default))


def get_config_multiline_option(parser: ConfigParser,
                                section: str,
                                option: str,
                                default: List[str] = None) -> List[str]:
    """
    Retrieves a multi-line string value from a parser as a list of strings
    (one per line, ignoring blank lines).

    Args:
        parser: instance of :class:`ConfigParser`
        section: section name within config file
        option: option (variable) name within that section
        default: value to return if option is absent (``None`` is mapped to
            ``[]``)

    Returns:
        list of strings

    Raises:
        ValueError: if the section is absent

    """
    default = default or []
    if not parser.has_section(section):
        raise ValueError("config missing section: " + section)
    try:
        multiline = parser.get(section, option)
        values = [x.strip() for x in multiline.splitlines() if x.strip()]
        return values
    except NoOptionError:
        return default


def read_config_multiline_options(obj: Any,
                                  parser: ConfigParser,
                                  section: str,
                                  options: Iterable[str]) -> None:
    """
    This is to :func:`read_config_string_options` as
    :func:`get_config_multiline_option` is to :func:`get_config_string_option`.
    """
    for o in options:
        setattr(obj, o, get_config_multiline_option(parser, section, o))


def get_config_bool_option(parser: ConfigParser,
                           section: str,
                           option: str,
                           default: bool = None) -> bool:
    """
    Retrieves a boolean value from a parser.

    Args:
        parser: instance of :class:`ConfigParser`
        section: section name within config file
        option: option (variable) name within that section
        default: value to return if option is absent

    Returns:
        string value

    Raises:
        ValueError: if the section is absent

    """
    if not parser.has_section(section):
        raise ValueError("config missing section: " + section)
    return parser.getboolean(section, option, fallback=default)


# =============================================================================
# Style 2
# =============================================================================

# =============================================================================
# Reading config files: style 2
# =============================================================================

def get_config_parameter(config: ConfigParser,
                         section: str,
                         param: str,
                         fn: Callable[[Any], Any],
                         default: Any) -> Any:
    """
    Fetch parameter from ``configparser`` ``.INI`` file.

    Args:
        config: :class:`ConfigParser` object
        section: section name within config file
        param: name of parameter within section
        fn: function to apply to string parameter (e.g. ``int``)
        default: default value

    Returns:
        parameter value, or ``None`` if ``default is None``, or ``fn(default)``
    """
    try:
        value = fn(config.get(section, param))
    except (TypeError, ValueError, NoOptionError):
        log.warning("Configuration variable {} not found or improper; "
                    "using default of {}", param, default)
        if default is None:
            value = default
        else:
            value = fn(default)
    return value


def get_config_parameter_boolean(config: ConfigParser,
                                 section: str,
                                 param: str,
                                 default: bool) -> bool:
    """
    Get Boolean parameter from ``configparser`` ``.INI`` file.

    Args:
        config: :class:`ConfigParser` object
        section: section name within config file
        param: name of parameter within section
        default: default value
    Returns:
        parameter value, or default
    """
    try:
        value = config.getboolean(section, param)
    except (TypeError, ValueError, NoOptionError):
        log.warning("Configuration variable {} not found or improper; "
                    "using default of {}", param, default)
        value = default
    return value


def get_config_parameter_loglevel(config: ConfigParser,
                                  section: str,
                                  param: str,
                                  default: int) -> int:
    """
    Get ``loglevel`` parameter from ``configparser`` ``.INI`` file, e.g.
    mapping ``'debug'`` to ``logging.DEBUG``.

    Args:
        config: :class:`ConfigParser` object
        section: section name within config file
        param: name of parameter within section
        default: default value
    Returns:
        parameter value, or default
    """
    try:
        value = config.get(section, param).lower()
        if value == "debug":
            return logging.DEBUG  # 10
        elif value == "info":
            return logging.INFO
        elif value in ["warn", "warning"]:
            return logging.WARN
        elif value == "error":
            return logging.ERROR
        elif value in ["critical", "fatal"]:
            return logging.CRITICAL  # 50
        else:
            raise ValueError
    except (TypeError, ValueError, NoOptionError, AttributeError):
        log.warning("Configuration variable {} not found or improper; "
                    "using default of {}", param, default)
        return default


def get_config_parameter_multiline(config: ConfigParser,
                                   section: str,
                                   param: str,
                                   default: List[str]) -> List[str]:
    """
    Get multi-line string parameter from ``configparser`` ``.INI`` file,
    as a list of strings (one per line, ignoring blank lines).

    Args:
        config: :class:`ConfigParser` object
        section: section name within config file
        param: name of parameter within section
        default: default value
    Returns:
        parameter value, or default
    """
    try:
        multiline = config.get(section, param)
        return [x.strip() for x in multiline.splitlines() if x.strip()]
    except (TypeError, ValueError, NoOptionError):
        log.warning("Configuration variable {} not found or improper; "
                    "using default of {}", param, default)
        return default
