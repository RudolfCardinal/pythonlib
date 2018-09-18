#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/alembic_ops.py

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

**Support functions for Alembic, specifically to support view creation.**

From http://alembic.readthedocs.org/en/latest/cookbook.html.

HAS NO TYPE ANNOTATIONS - Alembic uses ``inspect.getargspec()``, which chokes
on them.
"""

from alembic.operations import Operations, MigrateOperation


# =============================================================================
# The thing (e.g. view) we are representing
# =============================================================================

class ReplaceableObject(object):
    def __init__(self, name, sqltext):
        """
        Object that can be passed to the ``create_view()`` and similar
        functions that we will register within the ``alembic.op`` namespace.
        
        See http://alembic.zzzcomputing.com/en/latest/cookbook.html#replaceable-objects

        Args:
            name:
                e.g. name of a view, such as ``subject_session_view``

            sqltext:
                e.g. SQL to create the view, such as

                .. code-block:: sql

                    SELECT
                        C.subject,
                        S.*
                    FROM
                        config C
                        INNER JOIN session S ON S.config_id = C.config_id

        """  # noqa
        self.name = name
        self.sqltext = sqltext


# =============================================================================
# An operation that can be reversed
# =============================================================================

class ReversibleOp(MigrateOperation):
    """
    Represents a DDL (SQL) migration operation that can be reversed; e.g. the
    combination of ``CREATE VIEW`` and ``DROP VIEW``.
    """
    def __init__(self, target):
        """
        Args:
            target: instance of :class:`.ReplaceableObject`
        """
        self.target = target

    @classmethod
    def invoke_for_target(cls, operations, target):
        """
        Invokes the operation.

        Args:
            operations: instance of ``alembic.operations.base.Operations``
            target: instance of :class:`.ReplaceableObject`

        Returns:
            result of ``alembic.operations.base.Operations.invoke``
            performed upon an instance of this class initialized with
            ``target``
        """
        op = cls(target)
        return operations.invoke(op)

    def reverse(self):
        """
        Returns:
            the ``MigrateOperation`` representing the reverse of this operation
        """
        raise NotImplementedError()

    @classmethod
    def _get_object_from_version(cls, operations, ident):
        """
        Returns a Python object from an Alembic migration module (script).

        Args:
            operations: instance of ``alembic.operations.base.Operations``
            ident: string of the format ``version.objname``

        Returns:
            the object whose name is ``objname`` within the Alembic migration
            script identified by ``version``
        """
        version, objname = ident.split(".")

        module_ = operations.get_context().script.get_revision(version).module
        obj = getattr(module_, objname)
        return obj

    @classmethod
    def replace(cls, operations, target, replaces=None, replace_with=None):

        if replaces:
            old_obj = cls._get_object_from_version(operations, replaces)
            drop_old = cls(old_obj).reverse()
            create_new = cls(target)
        elif replace_with:
            old_obj = cls._get_object_from_version(operations, replace_with)
            drop_old = cls(target).reverse()
            create_new = cls(old_obj)
        else:
            raise TypeError("replaces or replace_with is required")

        operations.invoke(drop_old)
        operations.invoke(create_new)


# =============================================================================
# Operations that will become part of the op.* namespace
# =============================================================================

@Operations.register_operation("create_view", "invoke_for_target")
@Operations.register_operation("replace_view", "replace")
class CreateViewOp(ReversibleOp):
    """
    Represents ``CREATE VIEW`` (reversed by ``DROP VIEW``).
    """
    def reverse(self):
        return DropViewOp(self.target)


@Operations.register_operation("drop_view", "invoke_for_target")
class DropViewOp(ReversibleOp):
    """
    Represents ``DROP VIEW`` (reversed by ``CREATE VIEW``).
    """
    def reverse(self):
        return CreateViewOp(self.view)


@Operations.register_operation("create_sp", "invoke_for_target")
@Operations.register_operation("replace_sp", "replace")
class CreateSPOp(ReversibleOp):
    """
    Represents ``CREATE FUNCTION`` (reversed by ``DROP FUNCTION``)
    [sp = stored procedure].
    """
    def reverse(self):
        return DropSPOp(self.target)


@Operations.register_operation("drop_sp", "invoke_for_target")
class DropSPOp(ReversibleOp):
    """
    Represents ``DROP FUNCTION`` (reversed by ``CREATE FUNCTION``)
    [sp = stored procedure].
    """
    def reverse(self):
        return CreateSPOp(self.target)


# =============================================================================
# Implementation of these operations
# =============================================================================

@Operations.implementation_for(CreateViewOp)
def create_view(operations, operation):
    """
    Implements ``CREATE VIEW``.

    Args:
        operations: instance of ``alembic.operations.base.Operations``
        operation: instance of :class:`.ReversibleOp`

    Returns:
        ``None``
    """
    operations.execute("CREATE VIEW %s AS %s" % (
        operation.target.name,
        operation.target.sqltext
    ))


@Operations.implementation_for(DropViewOp)
def drop_view(operations, operation):
    """
    Implements ``DROP VIEW``.

    Args:
        operations: instance of ``alembic.operations.base.Operations``
        operation: instance of :class:`.ReversibleOp`

    Returns:
        ``None``
    """
    operations.execute("DROP VIEW %s" % operation.target.name)


@Operations.implementation_for(CreateSPOp)
def create_sp(operations, operation):
    """
    Implements ``CREATE FUNCTION``.

    Args:
        operations: instance of ``alembic.operations.base.Operations``
        operation: instance of :class:`.ReversibleOp`

    Returns:
        ``None``
    """
    operations.execute(
        "CREATE FUNCTION %s %s" % (
            operation.target.name, operation.target.sqltext
        )
    )


@Operations.implementation_for(DropSPOp)
def drop_sp(operations, operation):
    """
    Implements ``DROP FUNCTION``.

    Args:
        operations: instance of ``alembic.operations.base.Operations``
        operation: instance of :class:`.ReversibleOp`

    Returns:
        ``None``
    """
    operations.execute("DROP FUNCTION %s" % operation.target.name)
