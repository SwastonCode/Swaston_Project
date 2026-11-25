"""
Профиль пользователя.
"""
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import func, select

from base import async_session
from crud import get_or_create_user
from models import Reaction, ReactionType, Submission

router = Router(name="profile")


@router.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message) -> None:
    async with async_session() as session:
        user, _ = await get_or_create_user(session, message.from_user.id, message.from_user.username)

        submissions_count = await session.scalar(
            select(func.count()).select_from(Submission).where(Submission.user_id == user.id)
        )
        likes_received = await session.scalar(
            select(func.coalesce(func.sum(Submission.likes_count), 0)).where(Submission.user_id == user.id)
        )
        dislikes_received = await session.scalar(
            select(func.coalesce(func.sum(Submission.dislikes_count), 0)).where(Submission.user_id == user.id)
        )
        comments_received = await session.scalar(
            select(func.coalesce(func.sum(Submission.comments_count), 0)).where(Submission.user_id == user.id)
        )

        status = "🔴 Заблокирован" if user.is_banned else "🟢 Активен"

        text = (
            f"👤 <b>Профиль</b>\n\n"
            f"Username: @{user.username or '—'}\n"
            f"Telegram ID: {user.telegram_id}\n"
            f"Дата регистрации: {user.registered_at.strftime('%d.%m.%Y')}\n"
            f"Роль: {user.role.value}\n\n"
            f"Опубликовано проектов: {submissions_count}\n"
            f"Получено лайков: {likes_received}\n"
            f"Получено дизлайков: {dislikes_received}\n"
            f"Комментариев к проектам: {comments_received}\n\n"
            f"Предупреждений: {user.warnings}\n"
            f"Отметок о подозрительных исходниках: {user.virus_marks_count}\n"
            f"Банов: {user.bans_count}\n"
            f"Статус: {status}"
        )

    await message.answer(text, parse_mode="HTML")
