#!/usr/bin/env python
# cardinal_pythonlib/bulk_email/models.py

"""
===============================================================================

    Original code copyright (C) 2009-2021 Rudolf Cardinal (rudolf@pobox.com).

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

SQLAlchemy models for the simple bulk e-mail tool.

"""

# =============================================================================
# Imports
# =============================================================================

import datetime
import logging
import sys
from typing import Any, Iterable, Tuple

from sqlalchemy.event import listens_for
from sqlalchemy.orm.attributes import instance_state
from sqlalchemy.orm.exc import NoResultFound
# noinspection PyProtectedMember
from sqlalchemy.orm.session import make_transient, Session
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import and_, exists

from cardinal_pythonlib.bulk_email.constants import (
    CONTENT_TYPE_MAX_LENGTH,
    ENCODING_NAME_MAX_LENGTH,
    FERNET_KEY_BASE64_LENGTH,
    HOSTNAME_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
)
from cardinal_pythonlib.colander_utils import EMAIL_ADDRESS_MAX_LEN
from cardinal_pythonlib.email.sendmail import (
    ASCII,
    CONTENT_TYPE_TEXT,
    is_email_valid,
    UTF8,
)
from cardinal_pythonlib.sqlalchemy.orm_query import CountStarSpecializedQuery
from cardinal_pythonlib.sysops import EXIT_FAILURE

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("First, please install the 'cryptography' module with "
          "'pip install cryptography'.")
    sys.exit(EXIT_FAILURE)

log = logging.getLogger(__name__)


# =============================================================================
# The master SQLAlchemy ORM class
# =============================================================================

Base = declarative_base()


def make_table_args(*args, **kwargs) -> Tuple[Any]:
    """
    SQLAlchemy allows several formats for __table_args__. The most generic
    is a tuple that is a sequence of e.g. constraints, with the last element
    being a dictionary of keyword arguments.
    """
    # Add standard ones:
    kwargs["mysql_engine"] = "InnoDB"
    kwargs["mysql_row_format"] = "DYNAMIC"
    kwargs["mysql_charset"] = "utf8mb4 COLLATE utf8mb4_unicode_ci"

    # Return the tuple:
    return tuple(args + (kwargs, ))


# =============================================================================
# Config
# =============================================================================

# noinspection PyUnusedLocal
@listens_for(Session, "before_flush")
def before_flush(session: Session, flush_context, instances) -> None:
    # https://docs.sqlalchemy.org/en/14/orm/events.html#sqlalchemy.orm.SessionEvents.before_flush  # noqa
    for instance in session.dirty:
        if not isinstance(instance, Config):
            continue
        if not session.is_modified(instance):
            continue
        if not instance_state(instance).has_identity:
            continue

        # make it transient
        instance.new_version(session)
        # re-add
        session.add(instance)


class Config(Base):
    """
    Stores records of configuration information.

    Maintains history (so the config for previous send jobs is visible), per:

    - https://docs.sqlalchemy.org/en/14/_modules/examples/versioned_rows/versioned_rows.html
    - https://docs.sqlalchemy.org/en/14/orm/examples.html#module-examples.versioned_rows
    """  # noqa

    __tablename__ = "config"
    __table_args__ = make_table_args(
        comment="Stores configuration records."
    )

    # -------------------------------------------------------------------------
    # Columns
    # -------------------------------------------------------------------------

    config_id = Column(
        Integer,
        # ... may not be supported by all databases; see
        # https://docs.sqlalchemy.org/en/14/core/constraints.html#check-constraint  # noqa
        # ... though MySQL has recently added this:
        # https://dev.mysql.com/doc/refman/8.0/en/create-table-check-constraints.html  # noqa
        primary_key=True,
        autoincrement=True,
        comment=f"Primary key."
    )
    database_creation_datetime = Column(
        DateTime,
        comment="Date/time this database was created."
    )
    host = Column(
        String(length=HOSTNAME_MAX_LENGTH),
        nullable=False,
        comment="Mail (SMTP) server hostname"
    )
    port = Column(
        Integer,
        nullable=False,
        comment="Mail (SMTP) server TCP port"
    )
    use_tls = Column(
        Boolean,
        nullable=False,
        comment="Use TLS?"
    )
    username = Column(
        String(length=USERNAME_MAX_LENGTH),
        nullable=False,
        comment="Mail (SMTP) server username"
    )
    password_encrypted = Column(
        String(length=PASSWORD_MAX_LENGTH),
        nullable=False,
        comment="Mail (SMTP) server password (reversibly encrypted)"
    )
    encryption_key = Column(
        String(length=FERNET_KEY_BASE64_LENGTH),
        nullable=False,
        comment="Encryption key for password"
    )
    time_between_emails = Column(
        Float,
        nullable=False,
        comment="Time (in seconds) between each e-mail."
    )

    # -------------------------------------------------------------------------
    # Creation and version control
    # -------------------------------------------------------------------------

    @classmethod
    def get_current_config(cls, session: Session) -> "Config":
        """
        Fetch the current config, or raise.
        """
        cfg = (
            session.query(cls)
            .order_by(cls.config_id.desc())
            .first()  # returns object or None
        )
        if cfg is None:
            error = "No configuration found. " \
                    "Run the 'configure' command first."
            log.critical(error)
            raise ValueError(error)
        return cfg

    @classmethod
    def get_or_create_config(cls, session: Session) -> "Config":
        """
        Fetch the current config, or make a new one.
        """
        cfg = (
            session.query(cls)
            .order_by(cls.config_id.desc())
            .first()  # returns object or None
        )
        if cfg is None:
            cfg = cls()
            session.add(cfg)
        return cfg

    def __init__(self, *args, **kwargs) -> None:
        """
        Default configuration.
        """
        super().__init__(*args, **kwargs)
        self.database_creation_datetime = datetime.datetime.now()

    # noinspection PyUnusedLocal
    def new_version(self, session: Session) -> None:
        """
        Called by listener (see above) when object is being saved.
        """
        # Make us transient (removes persistent identity).
        make_transient(self)

        # Set PK to None. A new PK will be generated on INSERT.
        self.config_id = None

    # -------------------------------------------------------------------------
    # Obscuring passwords
    # -------------------------------------------------------------------------

    @property
    def password(self) -> str:
        """
        Returns the plaintext password.
        """
        # Key
        key_b64_bytes = self.encryption_key.encode(ASCII)
        # Engine
        f = Fernet(key_b64_bytes)
        # Decryption
        encrypted_password_b64_bytes = self.password_encrypted.encode(ASCII)
        return f.decrypt(encrypted_password_b64_bytes).decode(UTF8)

    @password.setter
    def password(self, password: str) -> None:
        """
        Store the password using reversible encryption.
        """
        # Key
        key_b64_bytes = Fernet.generate_key()  # base64-encoded 32-byte key
        self.encryption_key = key_b64_bytes.decode(ASCII)  # str version
        # Engine
        f = Fernet(key_b64_bytes)
        # Encryption
        password_bytes = password.encode(UTF8)
        encrypted_b64_bytes = f.encrypt(password_bytes)  # base64-encoded
        self.password_encrypted = encrypted_b64_bytes.decode(ASCII)


# =============================================================================
# Recipient
# =============================================================================

class Recipient(Base):
    """
    Details of an e-mail recipient.
    """
    __tablename__ = "recipient"
    __table_args__ = make_table_args(
        comment="E-mail recipients."
    )

    # -------------------------------------------------------------------------
    # Columns
    # -------------------------------------------------------------------------

    recipient_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key."
    )  # type: int
    email = Column(
        String(length=EMAIL_ADDRESS_MAX_LEN),
        nullable=False,
        unique=True,
        comment="E-mail address."
    )

    # -------------------------------------------------------------------------
    # Creation
    # -------------------------------------------------------------------------

    @classmethod
    def fetch_or_add(cls, email: str, session: Session) -> "Recipient":
        """
        Fetch or create/add the recipient.
        """
        try:
            return session.query(cls).filter_by(
                email=email
            ).one()
        except NoResultFound:
            newvar = cls(email=email)
            session.add(newvar)
            return newvar

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not is_email_valid(self.email):
            raise ValueError(f"Invalid e-mail address: {self.email!r}")

    # -------------------------------------------------------------------------
    # Info
    # -------------------------------------------------------------------------

    @staticmethod
    def n_recipients(session: Session) -> int:
        query = CountStarSpecializedQuery([Recipient], session=session)
        return query.count_star()


# =============================================================================
# Content
# =============================================================================

class Content(Base):
    """
    Contents of an e-mail that will be, or has been, sent to one or many
    recipients.
    """
    __tablename__ = "content"
    __table_args__ = make_table_args(
        comment="Contents of an e-mail (without recipient details; these are "
                "templates that may be sent to multiple recipients)."
    )

    # -------------------------------------------------------------------------
    # Columns
    # -------------------------------------------------------------------------

    content_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key."
    )  # type: int
    from_addr = Column(
        String(length=EMAIL_ADDRESS_MAX_LEN),
        nullable=False,
        comment="From (sender's) e-mail address."
    )
    reply_to_addr = Column(
        String(length=EMAIL_ADDRESS_MAX_LEN),
        nullable=False,
        comment="Reply-To (sender's) e-mail address."
    )
    email_datetime = Column(
        DateTime,
        comment='E-mail creation date/time, or NULL for '
                '"the time of sending".'
    )
    subject = Column(
        Text,
        # There is no limit to the subject length in RFC 2822; you can have
        # multiple lines (each up to 998 characters).
        comment="E-mail subject"
    )
    body = Column(
        Text,
        comment="E-mail body"
    )
    content_type = Column(
        String(length=CONTENT_TYPE_MAX_LENGTH),
        nullable=False,
        default=CONTENT_TYPE_TEXT,
        server_default=CONTENT_TYPE_TEXT,
        comment=f"Character set (encoding). Default: {UTF8!r}."
    )
    charset = Column(
        String(length=ENCODING_NAME_MAX_LENGTH),
        nullable=False,
        default=UTF8,
        server_default=UTF8,
        comment=f"Character set (encoding). Default: {UTF8!r}."
    )

    # -------------------------------------------------------------------------
    # Info
    # -------------------------------------------------------------------------

    @staticmethod
    def n_templates(session: Session) -> int:
        query = CountStarSpecializedQuery([Content], session=session)
        return query.count_star()


# =============================================================================
# Job
# =============================================================================

class Job(Base):
    """
    A task to send one e-mail to one recipient.
    """
    __tablename__ = "job"
    __table_args__ = make_table_args(
        comment="Attempts to send e-mails, successfully or otherwise."
    )

    # -------------------------------------------------------------------------
    # Columns
    # -------------------------------------------------------------------------

    job_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key."
    )  # type: int
    recipient_id = Column(
        Integer,
        ForeignKey("recipient.recipient_id", ondelete="CASCADE"),
        nullable=False,
        comment="Which recipient? Foreign key to recipient.recipient_id"
    )
    content_id = Column(
        Integer,
        ForeignKey("content.content_id", ondelete="CASCADE"),
        nullable=False,
        comment="What content? Foreign key to content.content_id"
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    recipient = relationship("Recipient")  # type: Recipient
    content = relationship("Content")  # type: Content

    # -------------------------------------------------------------------------
    # Jobs to be done
    # -------------------------------------------------------------------------

    @staticmethod
    def _pending_job_query(session: Session) -> CountStarSpecializedQuery:
        return (
            CountStarSpecializedQuery([Job], session=session)
            .filter(
                ~exists().select_from(SendAttempt).where(
                    and_(
                        SendAttempt.job_id == Job.job_id,
                        SendAttempt.success == True  # noqa
                    )
                )
            )
        )

    @classmethod
    def gen_jobs_to_be_done(cls, session: Session) -> Iterable["Job"]:
        query = cls._pending_job_query(session)
        for job in query.order_by(Job.job_id).all():
            yield job

    @staticmethod
    def n_completed_jobs(session: Session) -> int:
        # noinspection PyPep8
        query = (
            CountStarSpecializedQuery([Job], session=session)
            .join(SendAttempt)
            .filter(SendAttempt.success == True)  # noqa
        )
        return query.count_star()

    @classmethod
    def n_pending_jobs(cls, session: Session) -> int:
        query = cls._pending_job_query(session)
        return query.count_star()

    @classmethod
    def clear_pending_jobs(cls, session: Session) -> None:
        query = cls._pending_job_query(session)
        query.delete(synchronize_session=False)


# =============================================================================
# Attempt
# =============================================================================

class SendAttempt(Base):
    """
    Records the attempt to send an e-mail. Success means that it was accepted
    by our local server -- that doesn't imply final delivery (e.g. if the
    address is wrong).
    """
    __tablename__ = "send_attempt"
    __table_args__ = make_table_args(
        comment="Attempts to send e-mails, successfully or otherwise."
    )

    # -------------------------------------------------------------------------
    # Columns
    # -------------------------------------------------------------------------

    send_attempt_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key."
    )  # type: int
    job_id = Column(
        Integer,
        ForeignKey("job.job_id", ondelete="CASCADE"),
        nullable=False,
        comment="Which job is this for? Foreign key to job.job_id"
    )
    config_id = Column(
        Integer,
        ForeignKey("config.config_id", ondelete="CASCADE"),
        nullable=False,
        comment="Which config was used? Foreign key to config.config_id"
    )
    when_attempt = Column(
        DateTime,
        nullable=False,
        comment="When was the attempt made?"
    )
    success = Column(
        Boolean,
        nullable=False,
        comment="Was the sending attempt successful?"
    )
    details = Column(
        Text,
        comment="If unsuccessful, error details may be here. If successful, "
                "success messages go here."
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    job = relationship("Job")  # type: Job
    config = relationship("Config")  # type: Config
