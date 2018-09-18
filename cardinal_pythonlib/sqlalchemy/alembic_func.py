#!/usr/bin/env python
# cardinal_pythonlib/sqlalchemy/alembic_func.py

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

**Support functions for Alembic, the migration tool for SQLAlchemy.**

"""

import logging
import os
import subprocess
from typing import Tuple

from alembic.config import Config
from alembic.util.exc import CommandError
# noinspection PyUnresolvedReferences
from alembic.runtime.migration import MigrationContext
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import create_engine

from cardinal_pythonlib.fileops import preserve_cwd
from cardinal_pythonlib.logs import BraceStyleAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceStyleAdapter(log)


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

DEFAULT_ALEMBIC_VERSION_TABLE = "alembic_version"


# =============================================================================
# Alembic revision/migration system
# =============================================================================
# http://stackoverflow.com/questions/24622170/using-alembic-api-from-inside-application-code  # noqa

def get_head_revision_from_alembic(
        alembic_config_filename: str,
        alembic_base_dir: str = None,
        version_table: str = DEFAULT_ALEMBIC_VERSION_TABLE) -> str:
    """
    Ask Alembic what its head revision is (i.e. where the Python code would
    like the database to be at).

    Arguments:
        alembic_config_filename: config filename
        alembic_base_dir: directory to start in, so relative paths in the
            config file work.
        version_table: table name for Alembic versions
    """
    if alembic_base_dir is None:
        alembic_base_dir = os.path.dirname(alembic_config_filename)
    os.chdir(alembic_base_dir)  # so the directory in the config file works
    config = Config(alembic_config_filename)
    script = ScriptDirectory.from_config(config)
    with EnvironmentContext(config,
                            script,
                            version_table=version_table):
        return script.get_current_head()


def get_current_revision(
        database_url: str,
        version_table: str = DEFAULT_ALEMBIC_VERSION_TABLE) -> str:
    """
    Ask the database what its current revision is.

    Arguments:
        database_url: SQLAlchemy URL for the database
        version_table: table name for Alembic versions
    """
    engine = create_engine(database_url)
    conn = engine.connect()
    opts = {'version_table': version_table}
    mig_context = MigrationContext.configure(conn, opts=opts)
    return mig_context.get_current_revision()


def get_current_and_head_revision(
        database_url: str,
        alembic_config_filename: str,
        alembic_base_dir: str = None,
        version_table: str = DEFAULT_ALEMBIC_VERSION_TABLE) -> Tuple[str, str]:
    """
    Returns a tuple of ``(current_revision, head_revision)``; see
    :func:`get_current_revision` and :func:`get_head_revision_from_alembic`.

    Arguments:
        database_url: SQLAlchemy URL for the database
        alembic_config_filename: config filename
        alembic_base_dir: directory to start in, so relative paths in the
            config file work.
        version_table: table name for Alembic versions
    """
    # Where we are
    head_revision = get_head_revision_from_alembic(
        alembic_config_filename=alembic_config_filename,
        alembic_base_dir=alembic_base_dir,
        version_table=version_table
    )
    log.info("Intended database version: {}", head_revision)

    # Where we want to be
    current_revision = get_current_revision(
        database_url=database_url,
        version_table=version_table
    )
    log.info("Current database version: {}", current_revision)

    # Are we where we want to be?
    return current_revision, head_revision


@preserve_cwd
def upgrade_database(
        alembic_config_filename: str,
        alembic_base_dir: str = None,
        starting_revision: str = None,
        destination_revision: str = "head",
        version_table: str = DEFAULT_ALEMBIC_VERSION_TABLE,
        as_sql: bool = False) -> None:
    """
    Use Alembic to upgrade our database.
    "revision" is the destination revision.

    See http://alembic.readthedocs.org/en/latest/api/runtime.html
    but also, in particular, ``site-packages/alembic/command.py``

    Arguments:
        alembic_config_filename:
            config filename

        alembic_base_dir:
            directory to start in, so relative paths in the config file work

        starting_revision:
            revision to start at (typically ``None`` to ask the database)

        destination_revision:
            revision to aim for (typically ``"head"`` to migrate to the latest
            structure)

        version_table: table name for Alembic versions

        as_sql:
            run in "offline" mode: print the migration SQL, rather than
            modifying the database. See
            http://alembic.zzzcomputing.com/en/latest/offline.html

    """

    if alembic_base_dir is None:
        alembic_base_dir = os.path.dirname(alembic_config_filename)
    os.chdir(alembic_base_dir)  # so the directory in the config file works
    config = Config(alembic_config_filename)
    script = ScriptDirectory.from_config(config)

    # noinspection PyUnusedLocal,PyProtectedMember
    def upgrade(rev, context):
        return script._upgrade_revs(destination_revision, rev)

    log.info("Upgrading database to revision '{}' using Alembic",
             destination_revision)

    with EnvironmentContext(config,
                            script,
                            fn=upgrade,
                            as_sql=as_sql,
                            starting_rev=starting_revision,
                            destination_rev=destination_revision,
                            tag=None,
                            version_table=version_table):
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
    
    Alembic compares the **state of the database** to the **state of the
    metadata**, and generates a migration that brings the former up to the
    latter. (It does **not** compare the most recent revision to the current
    metadata, so make sure your database is up to date with the most recent
    revision before running this!)
    
    You **must check** that the autogenerated revisions are sensible.
    
    How does it know where to look for the database?
    
        1. This function changes into the directory of the Alembic ``.ini``
           file and calls the external program
        
           .. code-block:: bash
        
                alembic -c ALEMBIC_INI_FILE revision --autogenerate -m MESSAGE --rev-id REVISION_ID
                
        2. The Alembic ``.ini`` file points (via the ``script_location``
           variable) to a directory containing your ``env.py``. Alembic loads
           this script.
           
        3. That script typically works out the database URL and calls further
           into the Alembic code.        
           
   See http://alembic.zzzcomputing.com/en/latest/autogenerate.html.

    Regarding filenames: the default ``n_sequence_chars`` of 4 is like Django
    and gives files with names like

    .. code-block:: none

        0001_x.py, 0002_y.py, ...

    NOTE THAT TO USE A NON-STANDARD ALEMBIC VERSION TABLE, YOU MUST SPECIFY
    THAT IN YOUR ``env.py`` (see e.g. CamCOPS).

    Args:
        alembic_ini_file: filename of Alembic ``alembic.ini`` file
        alembic_versions_dir: directory in which you keep your Python scripts,
            one per Alembic revision
        message: message to be associated with this revision
        n_sequence_chars: number of numerical sequence characters to use in the
            filename/revision (see above).
    """  # noqa
    _, _, existing_version_filenames = next(os.walk(alembic_versions_dir),
                                            (None, None, []))
    existing_version_filenames = [
        x for x in existing_version_filenames if x != "__init__.py"]
    log.debug("Existing Alembic version script filenames: {!r}",
              existing_version_filenames)
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

    log.info(
        """
Generating new revision with Alembic...
    Last revision was: {}
    New revision will be: {}
    [If it fails with "Can't locate revision identified by...", you might need
    to DROP the Alembic version table (by default named 'alembic_version', but
    you may have elected to change that in your env.py.]
        """,
        current_seq_str,
        new_seq_str
    )

    alembic_ini_dir = os.path.dirname(alembic_ini_file)
    os.chdir(alembic_ini_dir)
    cmdargs = ['alembic',
               '-c', alembic_ini_file,
               'revision',
               '--autogenerate',
               '-m', message,
               '--rev-id', new_seq_str]
    log.info("From directory {!r}, calling: {!r}", alembic_ini_dir, cmdargs)
    subprocess.call(cmdargs)


def stamp_allowing_unusual_version_table(
        config: Config,
        revision: str,
        sql: bool = False,
        tag: str = None,
        version_table: str = DEFAULT_ALEMBIC_VERSION_TABLE) -> None:
    """
    Stamps the Alembic version table with the given revision; don't run any
    migrations.

    This function is a clone of ``alembic.command.stamp()``, but allowing
    ``version_table`` to change. See
    http://alembic.zzzcomputing.com/en/latest/api/commands.html#alembic.command.stamp
    """  # noqa

    script = ScriptDirectory.from_config(config)

    starting_rev = None
    if ":" in revision:
        if not sql:
            raise CommandError("Range revision not allowed")
        starting_rev, revision = revision.split(':', 2)

    # noinspection PyUnusedLocal
    def do_stamp(rev: str, context):
        # noinspection PyProtectedMember
        return script._stamp_revs(revision, rev)

    with EnvironmentContext(config,
                            script,
                            fn=do_stamp,
                            as_sql=sql,
                            destination_rev=revision,
                            starting_rev=starting_rev,
                            tag=tag,
                            version_table=version_table):
        script.run_env()
