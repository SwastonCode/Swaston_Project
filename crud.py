"""
Набор функций доступа к данным. Роль модератора хранится прямо в users.role —
отдельной таблицы moderators не требуется (упрощение архитектуры из ТЗ).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Comment,
    ModerationLog,
    Reaction,
    ReactionType,
    Role,
    Sanction,
    SanctionType,
    Submission,
    SubmissionStatus,
    User,
    VirusReport,
)


# --- Users ---

async def get_user_by_tg_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> tuple[User, bool]:
    user = await get_user_by_tg_id(session, telegram_id)
    if user:
        if username and user.username != username:
            user.username = username
            await session.commit()
        return user, False
    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, True


async def set_captcha_passed(session: AsyncSession, user: User) -> None:
    user.captcha_passed = True
    await session.commit()


async def bootstrap_owner(session: AsyncSession, owner_tg_id: int) -> None:
    user, _ = await get_or_create_user(session, owner_tg_id, None)
    if user.role != Role.OWNER:
        user.role = Role.OWNER
        await session.commit()


def is_moderator_role(role: Role) -> bool:
    return role in (Role.MODERATOR, Role.SENIOR_MODERATOR, Role.ADMINISTRATOR, Role.OWNER)


# --- Submissions ---

async def generate_submission_code(session: AsyncSession) -> str:
    count = await session.scalar(select(func.count()).select_from(Submission))
    return f"SRC-{(count or 0) + 1:06d}"


async def create_submission(session: AsyncSession, **kwargs) -> Submission:
    code = await generate_submission_code(session)
    submission = Submission(code=code, **kwargs)
    session.add(submission)
    await session.commit()
    await session.refresh(submission)
    return submission


async def get_submission(session: AsyncSession, submission_id: int) -> Submission | None:
    return await session.get(Submission, submission_id)


async def get_submission_by_code(session: AsyncSession, code: str) -> Submission | None:
    result = await session.execute(select(Submission).where(Submission.code == code))
    return result.scalar_one_or_none()


async def set_submission_status(
    session: AsyncSession,
    submission: Submission,
    status: SubmissionStatus,
    moderator_id: int,
    rejection_reason: str | None = None,
) -> None:
    submission.status = status
    submission.moderated_by = moderator_id
    submission.moderated_at = datetime.utcnow()
    if rejection_reason:
        submission.rejection_reason = rejection_reason
    await session.commit()


async def list_approved_submissions(
    session: AsyncSession,
    platform: str | None = None,
    language: str | None = None,
    order_by_popularity: bool = False,
    limit: int = 10,
    offset: int = 0,
) -> list[Submission]:
    query = select(Submission).where(Submission.status == SubmissionStatus.APPROVED)
    if platform:
        query = query.where(Submission.platform == platform)
    if language:
        query = query.where(Submission.language.ilike(language))
    if order_by_popularity:
        query = query.order_by(Submission.likes_count.desc())
    else:
        query = query.order_by(Submission.created_at.desc())
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    return list(result.scalars().all())


# --- Reactions ---

async def toggle_reaction(
    session: AsyncSession, submission: Submission, user: User, reaction_type: ReactionType
) -> ReactionType | None:
    """
    Возвращает итоговое состояние реакции пользователя (None — реакция снята).
    Обновляет счётчики submission.
    """
    result = await session.execute(
        select(Reaction).where(Reaction.submission_id == submission.id, Reaction.user_id == user.id)
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        session.add(Reaction(submission_id=submission.id, user_id=user.id, type=reaction_type))
        _bump_counter(submission, reaction_type, +1)
        await session.commit()
        return reaction_type

    if existing.type == reaction_type:
        _bump_counter(submission, reaction_type, -1)
        await session.delete(existing)
        await session.commit()
        return None

    _bump_counter(submission, existing.type, -1)
    _bump_counter(submission, reaction_type, +1)
    existing.type = reaction_type
    await session.commit()
    return reaction_type


def _bump_counter(submission: Submission, reaction_type: ReactionType, delta: int) -> None:
    if reaction_type == ReactionType.LIKE:
        submission.likes_count = max(0, submission.likes_count + delta)
    else:
        submission.dislikes_count = max(0, submission.dislikes_count + delta)


# --- Virus reports ---

async def add_virus_report(session: AsyncSession, submission: Submission, moderator: User) -> bool:
    """Возвращает True, если отметка добавлена, False — если модератор уже отмечал эту заявку."""
    result = await session.execute(
        select(VirusReport).where(
            VirusReport.submission_id == submission.id, VirusReport.moderator_id == moderator.id
        )
    )
    if result.scalar_one_or_none() is not None:
        return False

    session.add(VirusReport(submission_id=submission.id, moderator_id=moderator.id))

    author = await session.get(User, submission.user_id)
    if author:
        author.virus_marks_count += 1

    await session.commit()
    return True


async def count_user_virus_marks(session: AsyncSession, user_id: int) -> int:
    author = await session.get(User, user_id)
    return author.virus_marks_count if author else 0


# --- Sanctions ---

async def apply_sanction(
    session: AsyncSession,
    user: User,
    moderator: User,
    sanction_type: SanctionType,
    reason: str,
    expires_at: datetime | None,
) -> Sanction:
    sanction = Sanction(
        user_id=user.id,
        moderator_id=moderator.id,
        type=sanction_type,
        reason=reason,
        expires_at=expires_at,
    )
    session.add(sanction)

    if sanction_type == SanctionType.UNBAN:
        user.is_banned = False
        user.banned_until = None
    else:
        user.is_banned = True
        user.bans_count += 1
        user.banned_until = expires_at  # None == перманентный бан

    await session.commit()
    await session.refresh(sanction)
    return sanction


async def list_user_sanctions(session: AsyncSession, user_id: int) -> list[Sanction]:
    result = await session.execute(
        select(Sanction).where(Sanction.user_id == user_id).order_by(Sanction.created_at.desc())
    )
    return list(result.scalars().all())


# --- Moderation log ---

async def log_action(
    session: AsyncSession,
    moderator_id: int,
    action: str,
    target_type: str,
    target_id: int,
    details: str | None = None,
) -> None:
    session.add(
        ModerationLog(
            moderator_id=moderator_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )
    await session.commit()


# --- Comments stats ---

async def register_comment(session: AsyncSession, submission: Submission, user: User, telegram_message_id: int) -> None:
    session.add(Comment(submission_id=submission.id, user_id=user.id, telegram_message_id=telegram_message_id))
    submission.comments_count += 1
    await session.commit()
