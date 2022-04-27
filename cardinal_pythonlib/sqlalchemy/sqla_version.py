#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/schema.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Version checks/constants for SQLAlchemy.**

"""

from semantic_version import Version
import sqlalchemy

SQLA_VERSION = Version(sqlalchemy.__version__)
SQLA_SUPPORTS_POOL_PRE_PING = SQLA_VERSION >= Version("1.2.0")
SQLA_SUPPORTS_MYSQL_UPSERT = SQLA_VERSION >= Version("1.2.0")
# "upsert" = INSERT ... ON DUPLICATE KEY UPDATE
