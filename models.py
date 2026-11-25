"""
Модели БД: users, submissions, reactions, virus_reports,
sanctions, moderation_logs, moderators.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Role(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    SENIOR_MODERATOR = "senior_moderator"
    ADMINISTRATOR = "administrator"
    OWNER = "owner"


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    VIRUS = "virus"


class Platform(str, enum.Enum):
    ANDROID = "Android"
    WINDOWS = "Windows"
    LINUX = "Linux"
    IOS = "iOS"
    WEB = "Web"
    OTHER = "Other"


class ReactionType(str, enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"


class SanctionType(str, enum.Enum):
    TEMP_HOURS = "temp_hours"
    TEMP_DAYS = "temp_days"
    PERMANENT = "permanent"
    UNBAN = "unban"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.USER)

    warnings: Mapped[int] = mapped_column(Integer, default=0)
    virus_marks_count: Mapped[int] = mapped_column(Integer, default=0)
    bans_count: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    banned_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    captcha_passed: Mapped[bool] = mapped_column(Boolean, default=False)

    submissions: Mapped[list["Submission"]] = relationship(back_populates="author")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # SRC-000124

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="submissions")

    title: Mapped[str] = mapped_column(String(128))
    platform: Mapped[Platform] = mapped_column(Enum(Platform))
    language: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(String(64), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(256), nullable=True)

    archive_file_id: Mapped[str] = mapped_column(String(256))  # telegram file_id
    archive_filename: Mapped[str] = mapped_column(String(256))
    screenshots_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-список file_id

    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus), default=SubmissionStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    moderated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    channel_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    dislikes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (UniqueConstraint("submission_id", "user_id", name="uq_reaction_submission_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[ReactionType] = mapped_column(Enum(ReactionType))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    telegram_message_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VirusReport(Base):
    __tablename__ = "virus_reports"
    __table_args__ = (UniqueConstraint("submission_id", "moderator_id", name="uq_virus_report_submission_mod"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    moderator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Sanction(Base):
    __tablename__ = "sanctions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    moderator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[SanctionType] = mapped_column(Enum(SanctionType))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    moderator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(32))  # submission / user
    target_id: Mapped[int] = mapped_column(Integer)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
