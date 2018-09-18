#!/usr/bin/env python
# cardinal_pythonlib/django/fields/isodatetimetz.py

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

**Django field class implementing storage of a date/time, with its timezone, in
a text field (in ISO-8601 format).**

"""


import datetime
import dateutil.parser
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.db import models
from django.db.models.fields import DateField, DateTimeField, Field
from django.utils import timezone

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# IsoDateTimeTzField
# =============================================================================

# -----------------------------------------------------------------------------
# Conversions: Python
# -----------------------------------------------------------------------------

def iso_string_to_python_datetime(
        isostring: str) -> Optional[datetime.datetime]:
    """
    Takes an ISO-8601 string and returns a ``datetime``.
    """
    if not isostring:
        return None  # if you parse() an empty string, you get today's date
    return dateutil.parser.parse(isostring)


def python_utc_datetime_to_sqlite_strftime_string(
        value: datetime.datetime) -> str:
    """
    Converts a Python datetime to a string literal compatible with SQLite,
    including the millisecond field.
    """
    millisec_str = str(round(value.microsecond / 1000)).zfill(3)
    return value.strftime("%Y-%m-%d %H:%M:%S") + "." + millisec_str


def python_localized_datetime_to_human_iso(value: datetime.datetime) -> str:
    """
    Converts a Python ``datetime`` that has a timezone to an ISO-8601 string
    with ``:`` between the hours and minutes of the timezone.

    Example:
        >>> import datetime
        >>> import pytz
        >>> x = datetime.datetime.now(pytz.utc)
        >>> python_localized_datetime_to_human_iso(x)
        '2017-08-21T20:47:18.952971+00:00'
    """
    s = value.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    return s[:29] + ":" + s[29:]


# -----------------------------------------------------------------------------
# Field
# -----------------------------------------------------------------------------

class IsoDateTimeTzField(models.CharField):
    """
    Django field for date/time stored in ISO format.
    Microsecond resolution; timezone-aware.
    Example sent TO the database:

    .. code-block:: none

        2015-11-11T22:21:37.000000+05:00

        YYYY-MM-DD HH:MM:SS uuuuuu TZ:TZ
        1234567890123456789012345678901234567890 ... so 32 chars

    Will also accept FROM the database any ISO-8601 format accepted by
    ``dateutil.parser.parse()``

    - Python side: ``datetime.datetime``

    - The database-specific bits are tricky.

      - In SQLite, the ``DATETIME()`` and ``STRFTIME()`` functions can be used
        to convert ISO strings to UTC, so that's a good basis for comparison.
        However, the actual comparisons, as always in SQLite, are string-based.

      - ``DATETIME(...)`` ends up like this:

        .. code-block:: none

            2015-11-11 22:21:37

        ``STRFTIME('%Y-%m-%d %H:%M:%f', ...)`` looks like this, allowing
        millisecond precision:

        .. code-block:: none

            2015-11-11 22:21:37.000
            2015-11-11 22:21:37.123

        The Django automatic RHS converter for datetime values looks like this:

        .. code-block:: none

            2015-11-11 22:21:37
            2015-11-11 22:21:37.123456

        ... http://stackoverflow.com/questions/14368290/django-datetimefield-and-timezone-now

        ... so a direct comparison with ``DATETIME`` works only if the
        microsecond component is zero (or you coerce it to zero via
        ``get_db_prep_value``), and a direct comparison to the ``STRFTIME``
        expression fails.

        Coercing the fractional seconds to zero via ``get_db_prep_value()``
        would make sub-second comparisons meaningless in the database. So we
        should avoid that, and operate as close to the database resolution as
        possible.

        That means that we have to alter the RHS in the same way we altered the
        LHS, and that means we can't use a transform...
        ... oh, hang on, I'm just underestimating ``get_db_prep_value()``; we
        .can coerce to exactly the thing yielded by SQLite's ``STRFTIME``, by
        .converting to a string!

        Next step: the data conversion specified for the RHS of a transform is
        governed by its ``output_field``. So when we're coercing to a date, we
        specify a ``DateField`` here, and all is happy. But for a ``datetime``,
        we should NOT specify ``DateTimeField``, because that will bypass the
        equality lookup from our custom field, and also bypass the RHS
        conversion (via ``get_db_prep_value()`` etc.).

        Specifically, for a ``DateTimeField``, conversion to a database value is
        done by

        .. code-block:: none

            django/db/models/fields/__init__.py : DateTimeField.get_prep_value
            django/db/backends/{backend}/operations.py
                : DatabaseOperations.value_to_db_datetime
                - for sqlite3: calls str(value) [via six.texttype]
                  and for a datetime, that gives
                    2015-11-17 00:00:00  # if microsecond == 0
                    2015-11-17 00:00:00.001000  # if microsecond != 0

        So for a proper conversion, we need to convert SQLite stuff to that.
        The MySQL backend does the same thing, but MySQL has a concept of a
        datetime anyway.

    - For MySQL, see also:

        https://docs.djangoproject.com/en/1.8/ref/databases/#fractional-seconds-support-for-time-and-datetime-fields

    """  # noqa
    # https://docs.djangoproject.com/en/1.8/ref/models/fields/#field-api-reference  # noqa

    description = "ISO-8601 date/time field with timezone, stored as text"

    def __init__(self, *args, **kwargs) -> None:
        """
        Declare that we're a ``VARCHAR(32)`` on the database side.
        """
        # https://docs.djangoproject.com/en/1.8/howto/custom-model-fields/
        kwargs['max_length'] = 32
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> Tuple[str, str, List[Any], Dict[str, Any]]:
        """
        Takes an instance and calculates the arguments to pass to ``__init__``
        to reconstruct it.
        """
        name, path, args, kwargs = super().deconstruct()
        del kwargs['max_length']
        return name, path, args, kwargs

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def from_db_value(self, value, expression, connection, context):
        """
        Convert database value to Python value.
        Called when data is loaded from the database.
        """
        # log.debug("from_db_value: {}, {}".format(value, type(value)))
        if value is None:
            return value
        if value == '':
            return None
        return iso_string_to_python_datetime(value)

    def to_python(self, value: Optional[str]) -> Optional[Any]:
        """
        Called during deserialization and during form ``clean()`` calls.
        Must deal with an instance of the correct type; a string; or ``None``
        (if the field allows ``null=True``).
        Should raise ``ValidationError`` if problems.
        """
        # https://docs.djangoproject.com/en/1.8/howto/custom-model-fields/
        # log.debug("to_python: {}, {}".format(value, type(value)))
        if isinstance(value, datetime.datetime):
            return value
        if value is None:
            return value
        if value == '':
            return None
        return iso_string_to_python_datetime(value)

    def get_prep_value(self, value):
        """
        Convert Python value to database value for QUERYING.
        We query with UTC, so this function converts datetime values to UTC.

        Calls to this function are followed by calls to ``get_db_prep_value()``,
        which is for backend-specific conversions.
        """
        log.debug("get_prep_value: {}, {}".format(value, type(value)))
        if not value:
            return ''
            # For underlying (database) string types, e.g. VARCHAR, this
            # function must always return a string type.
            # https://docs.djangoproject.com/en/1.8/howto/custom-model-fields/
        # Convert to UTC
        return value.astimezone(timezone.utc)

    def get_db_prep_value(self, value, connection, prepared=False):
        """
        Further conversion of Python value to database value for QUERYING.
        This follows ``get_prep_value()``, and is for backend-specific stuff.
        See notes above.
        """
        log.debug("get_db_prep_value: {}, {}".format(value, type(value)))
        value = super().get_db_prep_value(value, connection, prepared)
        if value is None:
            return value
        # log.debug("connection.settings_dict['ENGINE']: {}".format(
        #              connection.settings_dict['ENGINE']))
        if connection.settings_dict['ENGINE'] == 'django.db.backends.sqlite3':
            return python_utc_datetime_to_sqlite_strftime_string(value)
        return value

    def get_db_prep_save(self, value, connection, prepared=False):
        """
        Convert Python value to database value for SAVING.
        We save with full timezone information.
        """
        log.debug("get_db_prep_save: {}, {}".format(value, type(value)))
        if not value:
            return ''
            # For underlying (database) string types, e.g. VARCHAR, this
            # function must always return a string type.
            # https://docs.djangoproject.com/en/1.8/howto/custom-model-fields/
        return python_localized_datetime_to_human_iso(value)


# -----------------------------------------------------------------------------
# Conversions: MySQL
# -----------------------------------------------------------------------------

def iso_string_to_sql_utcdatetime_mysql(x: str) -> str:
    """
    Provides MySQL SQL to convert an ISO-8601-format string (with punctuation)
    to a ``DATETIME`` in UTC. The argument ``x`` is the SQL expression to be
    converted (such as a column name).
    """
    return (
        "CONVERT_TZ(STR_TO_DATE(LEFT({x}, 26),"
        "                       '%Y-%m-%dT%H:%i:%s.%f'),"
        "           RIGHT({x}, 6),"  # from timezone
        "           '+00:00')"  # to timezone
    ).format(x=x)
    # In MySQL:
    # 1. STR_TO_DATE(), with the leftmost 23 characters,
    #    giving microsecond precision, but not correct for timezone
    # 2. CONVERT_TZ(), converting from the timezone info in the rightmost 6
    #    characters to UTC (though losing fractional seconds)


def iso_string_to_sql_utcdate_mysql(x: str) -> str:
    """
    Provides MySQL SQL to convert an ISO-8601-format string (with punctuation)
    to a ``DATE`` in UTC. The argument ``x`` is the SQL expression to be
    converted (such as a column name).
    """
    return (
        "DATE(CONVERT_TZ(STR_TO_DATE(LEFT({x}, 26),"
        "                            '%Y-%m-%dT%H:%i:%s.%f'),"
        "                RIGHT({x}, 6),"
        "                '+00:00')"
    ).format(x=x)


def iso_string_to_sql_date_mysql(x: str) -> str:
    """
    Provides MySQL SQL to convert an ISO-8601-format string (with punctuation)
    to a ``DATE``, just by taking the date fields (without any timezone
    conversion). The argument ``x`` is the SQL expression to be converted (such
    as a column name).
    """
    return "STR_TO_DATE(LEFT({x}, 10), '%Y-%m-%d')".format(x=x)


# -----------------------------------------------------------------------------
# Conversions: SQLite
# -----------------------------------------------------------------------------

def iso_string_to_sql_utcdatetime_sqlite(x: str) -> str:
    """
    Provides SQLite SQL to convert a column to a ``DATETIME`` in UTC. The
    argument ``x`` is the SQL expression to be converted (such as a column
    name).

    Output like:

    .. code-block:: none

        2015-11-14 18:52:47.000
        2015-11-14 18:52:47.247

    Internally, we don't use ``DATETIME()``; using ``STRFTIME()`` allows
    millsecond precision.
    """
    return "STRFTIME('%Y-%m-%d %H:%M:%f', {x})".format(x=x)
    # This doesn't mind the 'T' in the middle, rounds to millisecond precision,
    # and corrects for any timezone at the end without having to tell it to
    # explicitly.
    # Try:
    # SELECT strftime('%Y-%m-%d %H:%M:%f', '2015-11-15T18:29:02.34544+05:00');
    #
    # http://www.sqlite.org/lang_datefunc.html


def iso_string_to_sql_utcdatetime_pythonformat_sqlite(x: str) -> str:
    """
    Provides SQLite SQL to convert a column to a ``DATETIME`` in UTC, in a
    string format that matches a common Python format. The argument ``x`` is
    the SQL expression to be converted (such as a column name).

    Output like

    .. code-block:: none

        2015-11-14 18:52:47
        2015-11-14 18:52:47.247000

    i.e.

    - gets rid of trailing ``.000`` for zero milliseconds, appends
      trailing ``000`` for everything else,
    - ... thus matching the output of Python's ``str(x)`` where ``x`` is a
      ``datetime``.
    - ... thus matching the RHS of a Django default ``datetime`` comparison.
    """
    return """
        CASE SUBSTR(STRFTIME('%f', {x}), 4, 3)
        WHEN '000' THEN STRFTIME('%Y-%m-%d %H:%M:%S', {x})
        ELSE STRFTIME('%Y-%m-%d %H:%M:%f', {x}) || '000'
        END
    """.format(x=x)


def iso_string_to_sql_utcdate_sqlite(x: str) -> str:
    """
    Provides SQLite SQL to convert a column to a ``DATE`` in UTC. The argument
    ``x`` is the SQL expression to be converted (such as a column name).
    """
    return "DATE({x})".format(x=x)


def iso_string_to_sql_date_sqlite(x: str) -> str:
    """
    Provides SQLite SQL to convert a column to a ``DATE``, just by taking the
    date fields (without any timezone conversion). The argument ``x`` is the
    SQL expression to be converted (such as a column name).
    """
    return "DATE(SUBSTR({x}, 1, 10))".format(x=x)


# -----------------------------------------------------------------------------
# Lookups
# -----------------------------------------------------------------------------

def isodt_lookup_mysql(lookup, compiler, connection,
                       operator) -> Tuple[str, Any]:
    """
    For a comparison "LHS *op* RHS", transforms the LHS from a column
    containing an ISO-8601 date/time into an SQL ``DATETIME``,
    for MySQL.
    """
    lhs, lhs_params = compiler.compile(lookup.lhs)
    rhs, rhs_params = lookup.process_rhs(compiler, connection)
    params = lhs_params + rhs_params
    return '{lhs} {op} {rhs}'.format(
        lhs=iso_string_to_sql_utcdatetime_mysql(lhs),
        op=operator,
        rhs=rhs,
    ), params


def isodt_lookup_sqlite(lookup, compiler, connection,
                        operator) -> Tuple[str, Any]:
    """
    For a comparison "LHS *op* RHS", transforms the LHS from a column
    containing an ISO-8601 date/time into an SQL ``DATETIME``,
    for SQLite.
    """
    lhs, lhs_params = compiler.compile(lookup.lhs)
    rhs, rhs_params = lookup.process_rhs(compiler, connection)
    params = lhs_params + rhs_params
    return '{lhs} {op} {rhs}'.format(
        lhs=iso_string_to_sql_utcdatetime_sqlite(lhs),
        op=operator,
        rhs=rhs,
    ), params
    # ... RHS conversion using STRFTIME() not necessary because we do the
    # appropriate thing in get_db_prep_value().


# noinspection PyAbstractClass
@IsoDateTimeTzField.register_lookup
class IsoDateTimeLessThan(models.Lookup):
    """
    Lookup for a '<' comparison where the LHS is a column containing an
    ISO-8601 field (and the RHS will be comparable to a ``DATETIME``).
    """
    lookup_name = 'lt'

    def as_mysql(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_mysql(self, compiler, connection, "<")

    def as_sqlite(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_sqlite(self, compiler, connection, "<")


# noinspection PyAbstractClass
@IsoDateTimeTzField.register_lookup
class IsoDateTimeLessThanEqual(models.Lookup):
    """
    Lookup for a '<=' comparison where the LHS is a column containing an
    ISO-8601 field (and the RHS will be comparable to a ``DATETIME``).
    """
    lookup_name = 'lte'

    def as_mysql(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_mysql(self, compiler, connection, "<=")

    def as_sqlite(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_sqlite(self, compiler, connection, "<=")


# noinspection PyAbstractClass
@IsoDateTimeTzField.register_lookup
class IsoDateTimeExact(models.Lookup):
    """
    Lookup for a '=' comparison where the LHS is a column containing an
    ISO-8601 field (and the RHS will be comparable to a ``DATETIME``).
    """
    lookup_name = 'exact'

    def as_mysql(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_mysql(self, compiler, connection, "=")

    def as_sqlite(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_sqlite(self, compiler, connection, "=")


# noinspection PyAbstractClass
@IsoDateTimeTzField.register_lookup
class IsoDateTimeGreaterThan(models.Lookup):
    """
    Lookup for a '>' comparison where the LHS is a column containing an
    ISO-8601 field (and the RHS will be comparable to a ``DATETIME``).
    """
    lookup_name = 'gt'

    def as_mysql(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_mysql(self, compiler, connection, ">")

    def as_sqlite(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_sqlite(self, compiler, connection, ">")


# noinspection PyAbstractClass
@IsoDateTimeTzField.register_lookup
class IsoDateTimeGreaterThanEqual(models.Lookup):
    """
    Lookup for a '>=' comparison where the LHS is a column containing an
    ISO-8601 field (and the RHS will be comparable to a ``DATETIME``).
    """
    lookup_name = 'gte'

    def as_mysql(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_mysql(self, compiler, connection, ">=")

    def as_sqlite(self, compiler, connection) -> Tuple[str, Any]:
        return isodt_lookup_sqlite(self, compiler, connection, ">=")


# -----------------------------------------------------------------------------
# Transforms
# -----------------------------------------------------------------------------

# noinspection PyAbstractClass
@IsoDateTimeTzField.register_lookup
class IsoStringToUtcDateTime(models.Transform):
    """
    SQL expression: converts ISO-8601 field into UTC DATETIME.
    """
    lookup_name = 'utc'

    # NOTE THAT SETTING output_field MEANS YOU HAVE TO MAKE THE OUTPUT
    # MATCH THE FORMAT EXPECTED FOR A DateTimeField. The class's own
    # get_db_prep_value(), etc., will NOT be called.
    @property
    def output_field(self) -> Field:
        return DateTimeField()

    # noinspection PyUnusedLocal
    def as_mysql(self, compiler, connection) -> Tuple[str, Any]:
        log.debug("IsoStringToUtcDateTime.as_mysql")
        lhs, params = compiler.compile(self.lhs)
        return iso_string_to_sql_utcdatetime_mysql(lhs), params

    def as_sqlite(self, compiler, connection,
                  **extra_context) -> Tuple[str, Any]:
        log.debug("IsoStringToUtcDateTime.as_sqlite")
        lhs, params = compiler.compile(self.lhs)
        return iso_string_to_sql_utcdatetime_pythonformat_sqlite(lhs), params


# noinspection PyAbstractClass
@IsoDateTimeTzField.register_lookup
class IsoStringToUtcDate(models.Transform):
    """
    SQL expression: converts ISO-8601 field into DATE, using the UTC date.
    """
    lookup_name = 'utcdate'

    @property
    def output_field(self) -> Field:
        return DateField()

    # noinspection PyUnusedLocal
    def as_mysql(self, compiler, connection) -> Tuple[str, Any]:
        log.debug("IsoStringToUtcDate.as_mysql")
        lhs, params = compiler.compile(self.lhs)
        return iso_string_to_sql_utcdate_mysql(lhs), params

    def as_sqlite(self, compiler, connection,
                  **extra_context) -> Tuple[str, Any]:
        log.debug("IsoStringToUtcDate.as_sqlite")
        lhs, params = compiler.compile(self.lhs)
        return iso_string_to_sql_utcdate_sqlite(lhs), params


# noinspection PyAbstractClass
@IsoDateTimeTzField.register_lookup
class IsoStringToSourceDate(models.Transform):
    """
    SQL expression: converts ISO-8601 field into DATE, using the date part of
    the local ISO time (not the UTC date).
    """
    lookup_name = 'sourcedate'

    @property
    def output_field(self) -> Field:
        return DateField()

    # noinspection PyUnusedLocal
    def as_mysql(self, compiler, connection) -> Tuple[str, Any]:
        log.debug("IsoStringToSourceDate.as_mysql")
        lhs, params = compiler.compile(self.lhs)
        return iso_string_to_sql_date_mysql(lhs), params

    def as_sqlite(self, compiler, connection,
                  **extra_context) -> Tuple[str, Any]:
        log.debug("IsoStringToSourceDate.as_sqlite")
        lhs, params = compiler.compile(self.lhs)
        return iso_string_to_sql_date_sqlite(lhs), params


# =============================================================================
# Testing an ISO-based millisecond-precision date/time field with timezone
# =============================================================================

"""
import logging
logging.basicConfig()
import datetime
import dateutil
import pytz
from django.db import models
from django.utils import timezone

class BlibbleTest(models.Model):
    at = IsoDateTimeTzField()
    # thing = models.PositiveSmallIntegerField()
    class Meta:
        managed = True
        db_table = 'consent_test'
        verbose_name_plural = "no ideas"

now = datetime.datetime.now(pytz.utc)
t = BlibbleTest(at=now)
time1 = dateutil.parser.parse("2015-11-11T22:21:37.000000+05:00")
t.save()
# BlibbleTest.objects.filter(at__lt=time1)

# Explicitly use transform:
BlibbleTest.objects.filter(at__utc=time1)
BlibbleTest.objects.filter(at__utc=now)
BlibbleTest.objects.filter(at__utcdate=time1)
BlibbleTest.objects.filter(at__utcdate=now)
BlibbleTest.objects.filter(at__sourcedate=time1)
BlibbleTest.objects.filter(at__sourcedate=now)

# Use 'exact' lookup
BlibbleTest.objects.filter(at=time1)
BlibbleTest.objects.filter(at=now)
"""
