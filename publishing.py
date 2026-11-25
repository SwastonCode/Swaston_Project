"""
Публикация одобренного исходника в публичный канал.
"""
from aiogram import Bot

import config
from base import async_session
from models import Submission, User
from kb_reactions import reactions_keyboard


def _format_post(submission: Submission, author: User) -> str:
    author_line = f"@{author.username}" if author.username else "аноним"
    return (
        f"<b>SWASTON PROJECT</b>\n\n"
        f"<b>Название:</b> {submission.title}\n"
        f"<b>Платформа:</b> {submission.platform.value}\n"
        f"<b>Язык:</b> {submission.language}\n"
        f"<b>Версия:</b> {submission.version}\n"
        f"<b>Автор:</b> {author_line}\n"
        f"<b>Описание:</b> {submission.description}\n"
        f"<b>Файл:</b> {submission.archive_filename}"
    )


async def publish_submission(bot: Bot, submission: Submission) -> None:
    async with async_session() as session:
        author = await session.get(User, submission.user_id)

    text = _format_post(submission, author)
    keyboard = reactions_keyboard(submission.id, submission.likes_count, submission.dislikes_count)

    message = await bot.send_document(
        chat_id=config.CHANNEL_ID,
        document=submission.archive_file_id,
        caption=text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    async with async_session() as session:
        db_submission = await session.get(Submission, submission.id)
        db_submission.channel_message_id = message.message_id
        await session.commit()
