#!/usr/bin/env python
# cardinal_pythonlib/argparse_func.py

"""
===============================================================================
    Copyright (C) 2009-2017 Rudolf Cardinal (rudolf@pobox.com).

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
"""

# noinspection PyProtectedMember
from argparse import (
    ArgumentParser,
    Namespace,
    _HelpAction,
    _SubParsersAction,
)
from typing import Any, List


class ShowAllSubparserHelpAction(_HelpAction):
    """
    Class to serve as the 'action' for an argparse master parser, which shows
    help for all subparsers. As per

    https://stackoverflow.com/questions/20094215/argparse-subparser-monolithic-help-output  # noqa
    """

    def __call__(self,
                 parser: ArgumentParser,
                 namespace: Namespace,
                 values: List[Any],  # ?
                 option_string: str = None) -> None:
        parser.print_help()
        sep = "-" * 79

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
