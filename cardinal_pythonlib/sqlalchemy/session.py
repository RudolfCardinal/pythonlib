#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/session.py

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

from typing import TYPE_CHECKING
import logging

from sqlalchemy.engine.base import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm.session import Session

if TYPE_CHECKING:
    from sqlalchemy.engine.url import URL

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Connection management
# =============================================================================

def get_engine_from_session(dbsession: Session) -> Engine:
    """
    Gets the SQLAlchemy Engine from a SQLAlchemy Session.
    """
    engine = dbsession.bind
    assert isinstance(engine, Engine)
    return engine


def get_safe_url_from_engine(engine: Engine) -> str:
    """
    Gets a URL from an Engine, obscuring the password.
    """
    raw_url = engine.url  # type: str
    url_obj = make_url(raw_url)  # type: URL
    return repr(url_obj)
    # The default repr() implementation calls
    # self.__to_string__(hide_password=False)


def get_safe_url_from_session(dbsession: Session) -> str:
    """
    Gets a URL from a Session, obscuring the password.
    """
    return get_safe_url_from_engine(get_engine_from_session(dbsession))
