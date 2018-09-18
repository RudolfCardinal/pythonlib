#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/session.py

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

**Functions to work with SQLAlchemy sessions/engines.**

"""

from typing import TYPE_CHECKING
import logging
import os

from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm.session import Session

if TYPE_CHECKING:
    from sqlalchemy.engine.url import URL

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Database URLs
# =============================================================================

SQLITE_MEMORY_URL = "sqlite://"


def make_mysql_url(username: str, password: str, dbname: str,
                   driver: str = "mysqldb", host: str = "localhost",
                   port: int = 3306, charset: str = "utf8") -> str:
    """
    Makes an SQLAlchemy URL for a MySQL database.
    """
    return "mysql+{driver}://{u}:{p}@{host}:{port}/{db}?charset={cs}".format(
        driver=driver,
        host=host,
        port=port,
        db=dbname,
        u=username,
        p=password,
        cs=charset,
    )


def make_sqlite_url(filename: str) -> str:
    """
    Makes an SQLAlchemy URL for a SQLite database.
    """
    absfile = os.path.abspath(filename)
    return "sqlite://{host}/{path}".format(host="", path=absfile)
    # ... makes it clear how it works! Ends up being sqlite:////abspath
    # or sqlite:///relpath. Also works with backslashes for Windows paths; see
    # http://docs.sqlalchemy.org/en/latest/core/engines.html#sqlite


# =============================================================================
# Connection management
# =============================================================================

def get_engine_from_session(dbsession: Session) -> Engine:
    """
    Gets the SQLAlchemy :class:`Engine` from a SQLAlchemy :class:`Session`.
    """
    engine = dbsession.bind
    assert isinstance(engine, Engine)
    return engine


def get_safe_url_from_engine(engine: Engine) -> str:
    """
    Gets a URL from an :class:`Engine`, obscuring the password.
    """
    raw_url = engine.url  # type: str
    url_obj = make_url(raw_url)  # type: URL
    return repr(url_obj)
    # The default repr() implementation calls
    # self.__to_string__(hide_password=False)


def get_safe_url_from_session(dbsession: Session) -> str:
    """
    Gets a URL from a :class:`Session`, obscuring the password.
    """
    return get_safe_url_from_engine(get_engine_from_session(dbsession))


def get_safe_url_from_url(url: str) -> str:
    """
    Converts an SQLAlchemy URL into a safe version that obscures the password.
    """
    engine = create_engine(url)
    return get_safe_url_from_engine(engine)
