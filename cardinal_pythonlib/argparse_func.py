#!/usr/bin/env python
# cardinal_pythonlib/argparse_func.py

"""
===============================================================================

    Original code copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).

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

**Functions to help with argparse.**

"""

# noinspection PyProtectedMember
from argparse import (
    _HelpAction,
    _SubParsersAction,
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    ArgumentTypeError,
    Namespace,
    RawDescriptionHelpFormatter,
)
from typing import Any, Dict, List, Type


# =============================================================================
# Argparse actions
# =============================================================================

class ShowAllSubparserHelpAction(_HelpAction):
    """
    Class to serve as the ``action`` for an ``argparse`` master parser that
    shows help for all subparsers. As per

    https://stackoverflow.com/questions/20094215/argparse-subparser-monolithic-help-output
    """  # noqa

    def __call__(self,
                 parser: ArgumentParser,
                 namespace: Namespace,
                 values: List[Any],  # ?
                 option_string: str = None) -> None:
        # 1. Print top-level help
        parser.print_help()
        sep = "=" * 79  # "-" less helpful when using grep for "--option"!

        # 2. Print help for all subparsers
        # noinspection PyProtectedMember
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, _SubParsersAction)
        ]
        messages = [""]  # type: List[str]
        for subparsers_action in subparsers_actions:
            for choice, subparser in subparsers_action.choices.items():
                messages.append(sep)
                messages.append("Help for command '{}'".format(choice))
                messages.append(sep)
                messages.append(subparser.format_help())
        print("\n".join(messages))

        parser.exit()


# =============================================================================
# Argparse formatters
# =============================================================================

class RawDescriptionArgumentDefaultsHelpFormatter(
        ArgumentDefaultsHelpFormatter,
        RawDescriptionHelpFormatter):
    """
    Combines the features of

    - :class:`RawDescriptionHelpFormatter` -- don't mangle the description
    - :class:`ArgumentDefaultsHelpFormatter` -- print argument defaults
    """
    pass


# =============================================================================
# Argparse types/checkers
# =============================================================================

def str2bool(v: str) -> bool:
    """
    ``argparse`` type that maps strings in case-insensitive fashion like this:
    
    .. code-block:: none
    
        argument strings                value
        ------------------------------- -----
        'yes', 'true', 't', 'y', '1'    True
        'no', 'false', 'f', 'n', '0'    False
     
    From
    https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse

    Specimen usage:
    
    .. code-block:: python
    
        parser.add_argument(
            "--nice", type=str2bool, nargs='?',
            const=True,  # if --nice is present with no parameter
            default=NICE,  # if the argument is entirely absent
            help="Activate nice mode.")

    """  # noqa
    lv = v.lower()
    if lv in ('yes', 'true', 't', 'y', '1'):
        return True
    elif lv in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ArgumentTypeError('Boolean value expected.')


def positive_int(value: str) -> int:
    """
    ``argparse`` argument type that checks that its value is a positive
    integer.
    """
    try:
        ivalue = int(value)
        assert ivalue > 0
    except (AssertionError, TypeError, ValueError):
        raise ArgumentTypeError(
            "{!r} is an invalid positive int".format(value))
    return ivalue


def nonnegative_int(value: str) -> int:
    """
    ``argparse`` argument type that checks that its value is a non-negative
    integer.
    """
    try:
        ivalue = int(value)
        assert ivalue >= 0
    except (AssertionError, TypeError, ValueError):
        raise ArgumentTypeError(
            "{!r} is an invalid non-negative int".format(value))
    return ivalue


def percentage(value: str) -> float:
    """
    ``argparse`` argument type that checks that its value is a percentage (in
    the sense of a float in the range [0, 100]).
    """
    try:
        fvalue = float(value)
        assert 0 <= fvalue <= 100
    except (AssertionError, TypeError, ValueError):
        raise ArgumentTypeError(
            "{!r} is an invalid percentage value".format(value))
    return fvalue


class MapType(object):
    """
    ``argparse`` type maker that maps strings to a dictionary (map).
    """

    def __init__(self,
                 map_separator: str = ":",
                 pair_separator: str = ",",
                 strip: bool = True,
                 from_type: Type = str,
                 to_type: Type = str) -> None:
        """
        Args:
            map_separator:
                string that separates the "from" and "to" members of a pair
            pair_separator:
                string that separates different pairs
            strip:
                strip whitespace after splitting?
            from_type:
                type to coerce "from" values to; e.g. ``str``, ``int``
            to_type:
                type to coerce "to" values to; e.g. ``str``, ``int``
        """
        self.map_separator = map_separator
        self.pair_separator = pair_separator
        self.strip = strip
        self.from_type = from_type
        self.to_type = to_type

    def __call__(self, value: str) -> Dict:
        result = {}
        pairs = value.split(self.pair_separator)
        for pair in pairs:
            from_str, to_str = pair.split(self.map_separator)
            if self.strip:
                from_str = from_str.strip()
                to_str = to_str.strip()
            try:
                from_val = self.from_type(from_str)
            except (TypeError, ValueError):
                raise ArgumentTypeError(
                    "{!r} cannot be converted to type {!r}".format(
                        from_str, self.from_type))
            try:
                to_val = self.to_type(to_str)
            except (TypeError, ValueError):
                raise ArgumentTypeError(
                    "{!r} cannot be converted to type {!r}".format(
                        to_str, self.to_type))
            result[from_val] = to_val
        return result
