#!/usr/bin/env python
# cardinal_pythonlib/register_db_with_odbc.py

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

**Creates/registers an Access database via ODBC.**

See

- http://support.microsoft.com/kb/126606/EN-US

  .. code-block:: none
  
    CREATE_DBV2=<path name> <sort order>
        (to create version 2 Jet engine mdb file, Access 2, 16bit)
    CREATE_DBV3=<path name> <sort order>
        (to create version 3 Jet engine mdb file, Access 95, Access 97)
    CREATE_DBV4=<path name> <sort order>
        (to create version 4 Jet engine mdb file, Access 2000)
        
- http://code.activestate.com/recipes/414879-create-an-odbc-data-source/

- view-source:http://www.experts-exchange.com/Programming/Languages/Pascal/Delphi/Q_22020226.html

  - this instead suggests CREATE_DBV3 for Access 95, CREATE_DBV4 for Access 97,
    and CREATE_DB for Access 2000, but that's probably wrong

- http://vieka.com/esqldoc/esqlref/htm/odbcsqlconfigdatasource.htm

- http://code.google.com/p/opendbviewer/source/browse/trunk/src/dbconnector/win32adodb.py?spec=svn45&r=45

- http://msdn.microsoft.com/en-us/library/aa140021(v=office.10).aspx

  - ... indicates that programmatic creation of queries/views (via ADO)
    leads to "invisible" queries
    
- http://msaccessmemento.hubpages.com/hub/Stored_Procedure_in_MS_Access

  - ... additionally, stored procedures have no user interface

"""  # noqa

from __future__ import division, print_function, absolute_import
import ctypes
import os.path
import platform
import sys
from typing import List

ODBC_ADD_DSN = 1         # Add data source
ODBC_CONFIG_DSN = 2      # Configure (edit) data source
ODBC_REMOVE_DSN = 3      # Remove data source
ODBC_ADD_SYS_DSN = 4     # add a system DSN
ODBC_CONFIG_SYS_DSN = 5  # Configure a system DSN
ODBC_REMOVE_SYS_DSN = 6  # remove a system DSN
access_driver = "Microsoft Access Driver (*.mdb)"
nul = chr(0)


def create_sys_dsn(driver: str, **kw) -> bool:
    """
    (Windows only.)
    Create a system ODBC data source name (DSN).

    Args:
        driver: ODBC driver name
        kw: Driver attributes

    Returns:
        bool: was the DSN created?
    """
    attributes = []  # type: List[str]
    for attr in kw.keys():
        attributes.append("%s=%s" % (attr, kw[attr]))
    return bool(
        ctypes.windll.ODBCCP32.SQLConfigDataSource(0, ODBC_ADD_SYS_DSN,
                                                   driver,
                                                   nul.join(attributes))
    )


def create_user_dsn(driver: str, **kw) -> bool:
    """
    (Windows only.)
    Create a user ODBC data source name (DSN).

    Args:
        driver: ODBC driver name
        kw: Driver attributes

    Returns:
        bool: was the DSN created?
    """
    attributes = []  # type: List[str]
    for attr in kw.keys():
        attributes.append("%s=%s" % (attr, kw[attr]))
    return bool(
        ctypes.windll.ODBCCP32.SQLConfigDataSource(0, ODBC_ADD_DSN, driver,
                                                   nul.join(attributes))
    )


def register_access_db(fullfilename: str, dsn: str, description: str) -> bool:
    """
    (Windows only.)
    Registers a Microsoft Access database with ODBC.

    Args:
        fullfilename: filename of the existing database
        dsn: ODBC data source name to create
        description: description of the database

    Returns:
        bool: was the DSN created?

    """
    directory = os.path.dirname(fullfilename)
    return create_sys_dsn(
        access_driver,
        SERVER="",
        DESCRIPTION=description,
        DSN=dsn,
        DBQ=fullfilename,
        DefaultDir=directory
    )


def create_and_register_access97_db(filename: str,
                                    dsn: str,
                                    description: str) -> bool:
    """
    (Windows only.)
    Creates a Microsoft Access 97 database and registers it with ODBC.

    Args:
        filename: filename of the database to create
        dsn: ODBC data source name to create
        description: description of the database

    Returns:
        bool: was the DSN created?
    """
    fullfilename = os.path.abspath(filename)
    create_string = fullfilename + " General"
    # ... filename, space, sort order ("General" for English)
    return (create_user_dsn(access_driver, CREATE_DB3=create_string) and
            register_access_db(filename, dsn, description))


def create_and_register_access2000_db(filename: str,
                                      dsn: str,
                                      description: str) -> bool:
    """
    (Windows only.)
    Creates a Microsoft Access 2000 database and registers it with ODBC.

    Args:
        filename: filename of the database to create
        dsn: ODBC data source name to create
        description: description of the database

    Returns:
        bool: was the DSN created?
    """
    fullfilename = os.path.abspath(filename)
    create_string = fullfilename + " General"
    # ... filename, space, sort order ("General" for English)
    return (create_user_dsn(access_driver, CREATE_DB4=create_string) and
            register_access_db(filename, dsn, description))


def create_and_register_access_db(filename: str,
                                  dsn: str,
                                  description: str) -> bool:
    """
    (Windows only.)
    Creates a Microsoft Access database and registers it with ODBC.

    Args:
        filename: filename of the database to create
        dsn: ODBC data source name to create
        description: description of the database

    Returns:
        bool: was the DSN created?
    """
    fullfilename = os.path.abspath(filename)
    create_string = fullfilename + " General"
    # ... filename, space, sort order ("General" for English)
    return (create_user_dsn(access_driver, CREATE_DB=create_string) and
            register_access_db(filename, dsn, description))
    # likely defaults to Access 2000


if __name__ == "__main__":
    if platform.system() != "Windows":
        print("Only Windows supported.")
        sys.exit()
    if create_and_register_access_db("testaccessdb.mdb",
                                     "Test_Access_DB",
                                     "My test Access DB DSN"):
        print("DSN created")
    else:
        print("DSN not created")
