#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/logs.py

"""
===============================================================================
    Copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

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

import logging


def pre_disable_sqlalchemy_extra_echo_log() -> None:
    """
    If you create an SQLAlchemy Engine with echo=True, it creates an additional
    log to stdout, via

        sqlalchemy.engine.base.Engine.__init__()
        sqlalchemy.log.instance_logger()
        sqlalchemy.log.InstanceLogger.__init__()
            ... which checks that the logger has no handlers and if not calls:
        sqlalchemy.log._add_default_handler()
            ... which adds a handler to sys.stdout
    """
    log = logging.getLogger("sqlalchemy.engine.base.Engine")
    log.addHandler(logging.NullHandler())
