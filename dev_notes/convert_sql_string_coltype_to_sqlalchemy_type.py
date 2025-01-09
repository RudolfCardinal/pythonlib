# EXPLORATORY CODE ONLY.
#
# PROBLEM: Take a SQL string fragment representing a column type (e.g.
# "VARCHAR(32)", "STRING") and an SQLAlchemy dialect (a core one like mysql or
# sqlite, or a third-party one like databricks), and return the appropriate
# SQLAlchemy type as a TypeEngine class/instance.
#
# CURRENT IMPLEMENTATION:
#   cardinal_pythonlib.sqlalchemy.schema.get_sqla_coltype_from_dialect_str()
#   ... with its sub-function, _get_sqla_coltype_class_from_str()
#
# DISCUSSION AT: https://github.com/sqlalchemy/sqlalchemy/discussions/12230


# For exploring some files directly:
from sqlalchemy.inspection import inspect  # noqa: F401
import sqlalchemy.dialects.sqlite.base
import sqlalchemy.dialects.sqlite.pysqlite  # noqa: F401

# Test code for dialects:
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.dialects.mssql import dialect as MSSQLDialect
from sqlalchemy.dialects.mysql import dialect as MySQLDialect
from sqlalchemy.dialects.postgresql import dialect as PostgreSQLDialect
from sqlalchemy.dialects.sqlite import dialect as SQLiteDialect

# Third-party dialect
from databricks.sqlalchemy import DatabricksDialect

# Create instances to explore:
default_dialect = DefaultDialect()
postgresql_dialect = PostgreSQLDialect()
mssql_dialect = MSSQLDialect()
mysql_dialect = MySQLDialect()
sqlite_dialect = SQLiteDialect()
databricks_dialect = DatabricksDialect()

print(sqlite_dialect.ischema_names)

# The native ones all have an "ischema_names" dictionary, apart from
# DefaultDialect. The Databricks one doesn't.

# The way SQLAlchemy does this for real is via an Inspector, which passes on
# to the Dialect.
# Inspector: https://docs.sqlalchemy.org/en/20/core/reflection.html#sqlalchemy.engine.reflection.Inspector  # noqa: E501
# Engine: https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.Engine  # noqa: E501
# Dialect: https://docs.sqlalchemy.org/en/14/core/internals.html#sqlalchemy.engine.Dialect  # noqa: E501
# ... get_columns()
# ... type_descriptor(), convers generic SQLA type to dialect-specific type.
# DefaultDialect: https://docs.sqlalchemy.org/en/14/core/internals.html#sqlalchemy.engine.default.DefaultDialect  # noqa: E501

# I can't find a generic method. See discussion above: there isn't one.
