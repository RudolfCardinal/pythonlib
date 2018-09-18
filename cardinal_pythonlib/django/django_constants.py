#!/usr/bin/env python
# cardinal_pythonlib/django/django_constants.py

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

**Constants for use with Django.**

"""


class ConnectionVendors(object):
    """
    Constants for Django database connection vendors (database types).
    """
    MYSQL = 'mysql'  # built in; [1]
    ORACLE = 'oracle'  # built in; [1]
    POSTGRESQL = 'postgresql'  # built in; [1]
    SQLITE = 'sqlite'  # built in; [1]
    # [1] https://docs.djangoproject.com/en/1.10/howto/custom-lookups/#writing-alternative-implementations-for-existing-lookups  # noqa

    # I think this is HYPOTHETICAL: SQLSERVER = 'sqlserver'  # [2]
    # [2] https://docs.djangoproject.com/en/1.11/ref/models/expressions/

    MICROSOFT = 'microsoft'  # [3]
    # [3] "pip install django-mssql" = sqlserver_ado;
    #     https://bitbucket.org/Manfre/django-mssql/src/d44721ba17acf95da89f06bd7270dabc1cd33deb/sqlserver_ado/base.py?at=master&fileviewer=file-view-default  # noqa
