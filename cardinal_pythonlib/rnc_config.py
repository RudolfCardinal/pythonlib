#!/usr/bin/python
# -*- encoding: utf8 -*-

"""Support functions for config (.INI) file reading

Author: Rudolf Cardinal (rudolf@pobox.com)
Created: 16 Apr 2015
Last update: 24 Sep 2015

Copyright/licensing:

    Copyright (C) 2015-2015 Rudolf Cardinal (rudolf@pobox.com).

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""


# =============================================================================
# Config
# =============================================================================


def get_config_string_option(parser, section, option, default=None):
    if not parser.has_section(section):
        raise ValueError("config missing section: " + section)
    return parser.get(section, option, fallback=default)


def read_config_string_options(obj, parser, section, options, default=None):
    # enforce_str removed; ConfigParser always returns strings unless asked
    # specifically
    for o in options:
        setattr(obj, o, get_config_string_option(parser, section, o,
                                                 default=default))


def get_config_multiline_option(parser, section, option, default=None):
    default = default or []
    if not parser.has_section(section):
        raise ValueError("config missing section: " + section)
    try:
        multiline = parser.get(section, option)
        values = [x.strip() for x in multiline.splitlines() if x.strip()]
        return values
    except configparser.NoOptionError:
        return default


def read_config_multiline_options(obj, parser, section, options):
    for o in options:
        setattr(obj, o, get_config_multiline_option(parser, section, o))


def get_config_bool_option(parser, section, option, default=None):
    if not parser.has_section(section):
        raise ValueError("config missing section: " + section)
    return parser.getboolean(section, option, fallback=default)
