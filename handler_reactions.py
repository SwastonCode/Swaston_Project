"""
Лайки/дизлайки под публикациями в канале.
Одна реакция на пользователя; повторное нажатие снимает реакцию, другая — заменяет.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery

from base import async_session
from crud import get_or_create_user, get_submission, toggle_reaction
from models import ReactionType
from kb_reactions import reactions_keyboard

router = Router(name="reactions")


@router.callback_query(F.data.startswith("react:"))
async def on_reaction(callback: CallbackQuery) -> None:
    _, reaction_name, submission_id = callback.data.split(":")
    submission_id = int(submission_id)
    reaction_type = ReactionType.LIKE if reaction_name == "like" else ReactionType.DISLIKE

    async with async_session() as session:
        user, _ = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        submission = await get_submission(session, submission_id)
        if submission is None:
            await callback.answer("Пост не найден.", show_alert=True)
            return

        await toggle_reaction(session, submission, user, reaction_type)
        await session.refresh(submission)

        new_keyboard = reactions_keyboard(submission.id, submission.likes_count, submission.dislikes_count)

    await callback.message.edit_reply_markup(reply_markup=new_keyboard)
    await callback.answer()
