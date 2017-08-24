#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/alembic_func.py

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

import logging
import os
import subprocess
from typing import Tuple

from alembic.config import Config
# noinspection PyUnresolvedReferences
from alembic.migration import MigrationContext
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import create_engine

from cardinal_pythonlib.fileops import preserve_cwd

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Constants for Alembic
# =============================================================================
# https://alembic.readthedocs.org/en/latest/naming.html
# http://docs.sqlalchemy.org/en/latest/core/constraints.html#configuring-constraint-naming-conventions  # noqa

ALEMBIC_NAMING_CONVENTION = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    # "ck": "ck_%(table_name)s_%(constraint_name)s",  # too long?
    # ... https://groups.google.com/forum/#!topic/sqlalchemy/SIT4D8S9dUg
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}


# =============================================================================
# Alembic revision/migration system
# =============================================================================
# http://stackoverflow.com/questions/24622170/using-alembic-api-from-inside-application-code  # noqa

def get_head_revision_from_alembic(alembic_config_filename: str,
                                   alembic_base_dir: str = None) -> str:
    """
    Ask Alembic what its head revision is.
    Arguments:
        alembic_config_filename: config filename
        alembic_base_dir: directory to start in, so relative paths in the
            config file work.
    """
    if alembic_base_dir is None:
        alembic_base_dir = os.path.dirname(alembic_config_filename)
    os.chdir(alembic_base_dir)  # so the directory in the config file works
    config = Config(alembic_config_filename)
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def get_current_revision(database_url: str) -> str:
    """
    Ask the database what its current revision is.
    """
    engine = create_engine(database_url)
    conn = engine.connect()
    mig_context = MigrationContext.configure(conn)
    return mig_context.get_current_revision()


def get_current_and_head_revision(
        database_url: str,
        alembic_config_filename: str,
        alembic_base_dir: str = None) -> Tuple[str, str]:
    # Where we are
    head_revision = get_head_revision_from_alembic(
        alembic_config_filename, alembic_base_dir)
    log.info("Intended database version: {}".format(head_revision))

    # Where we want to be
    current_revision = get_current_revision(database_url)
    log.info("Current database version: {}".format(current_revision))

    # Are we where we want to be?
    return current_revision, head_revision


@preserve_cwd
def upgrade_database(alembic_config_filename: str,
                     alembic_base_dir: str = None,
                     destination_revision: str = "head") -> None:
    """
    Use Alembic to upgrade our database.
    "revision" is the destination revision.

    See http://alembic.readthedocs.org/en/latest/api/runtime.html
    but also, in particular, site-packages/alembic/command.py
    """

    if alembic_base_dir is None:
        alembic_base_dir = os.path.dirname(alembic_config_filename)
    os.chdir(alembic_base_dir)  # so the directory in the config file works
    config = Config(alembic_config_filename)
    script = ScriptDirectory.from_config(config)

    # noinspection PyUnusedLocal,PyProtectedMember
    def upgrade(rev, context):
        return script._upgrade_revs(destination_revision, rev)

    log.info("Upgrading database to revision '{}' using Alembic".format(
        destination_revision))

    with EnvironmentContext(config,
                            script,
                            fn=upgrade,
                            as_sql=False,
                            starting_rev=None,
                            destination_rev=destination_revision,
                            tag=None):
        script.run_env()

    log.info("Database upgrade completed")


@preserve_cwd
def create_database_migration_numbered_style(
        alembic_ini_file: str,
        alembic_versions_dir: str,
        message: str,
        n_sequence_chars: int = 4) -> None:
    """
    Create a new Alembic migration script.
    The default n_sequence_chars is like Django and gives files like
        0001_x.py, 0002_y.py, ...
    """
    _, _, existing_version_filenames = next(os.walk(alembic_versions_dir),
                                            (None, None, []))
    existing_version_filenames = [
        x for x in existing_version_filenames if x != "__init__.py"]
    log.debug("Existing Alembic version script filenames: " +
              repr(existing_version_filenames))
    current_seq_strs = [x[:n_sequence_chars]
                        for x in existing_version_filenames]
    current_seq_strs.sort()
    if not current_seq_strs:
        current_seq_str = None
        new_seq_no = 1
    else:
        current_seq_str = current_seq_strs[-1]
        new_seq_no = max(int(x) for x in current_seq_strs) + 1
    new_seq_str = str(new_seq_no).zfill(n_sequence_chars)

    log.info("""
Generating new revision with Alembic...
    Last revision was: {}
    New revision will be: {}
    [If it fails with "Can't locate revision identified by...", you might need
    to DROP the alembic_version table.]
        """.format(current_seq_str, new_seq_str))

    alembic_ini_dir = os.path.dirname(alembic_ini_file)
    os.chdir(alembic_ini_dir)
    subprocess.call(['alembic',
                     '-c', alembic_ini_file,
                     'revision',
                     '--autogenerate',
                     '-m', message,
                     '--rev-id', new_seq_str])
