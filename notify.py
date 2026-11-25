"""
Отправка заявки в группу модераторов.
"""
from aiogram import Bot

import config
from models import Submission, User
from kb_moderation import moderation_keyboard


def _format_submission_card(submission: Submission, author: User) -> str:
    author_line = f"@{author.username}" if author.username else f"id{author.telegram_id}"
    scan = submission.scan_result or "не выполнялось"
    return (
        f"🆕 <b>Новая заявка {submission.code}</b>\n\n"
        f"<b>Название:</b> {submission.title}\n"
        f"<b>Автор:</b> {author_line} (tg_id: {author.telegram_id})\n"
        f"<b>Платформа:</b> {submission.platform.value}\n"
        f"<b>Язык:</b> {submission.language}\n"
        f"<b>Версия:</b> {submission.version}\n"
        f"<b>Описание:</b> {submission.description}\n"
        f"<b>Лицензия:</b> {submission.license or '—'}\n"
        f"<b>GitHub:</b> {submission.github_url or '—'}\n\n"
        f"<b>Результат сканирования:</b> {scan}\n"
        f"<i>Результат сканирования не является гарантией безопасности.</i>"
    )


async def send_to_moderation(bot: Bot, submission: Submission, author: User) -> None:
    text = _format_submission_card(submission, author)
    await bot.send_message(
        chat_id=config.MOD_GROUP_ID,
        text=text,
        parse_mode="HTML",
        reply_markup=moderation_keyboard(submission.id),
    )
    # Пересылаем сам архив отдельным сообщением (по file_id, без повторной загрузки)
    await bot.send_document(
        chat_id=config.MOD_GROUP_ID,
        document=submission.archive_file_id,
        caption=f"Архив к заявке {submission.code}",
    )


async def notify_author_approved(bot: Bot, author: User, submission: Submission) -> None:
    await bot.send_message(
        chat_id=author.telegram_id,
        text=f"✅ Твоя заявка {submission.code} «{submission.title}» одобрена и опубликована в канале!",
    )


async def notify_author_rejected(bot: Bot, author: User, submission: Submission, reason: str) -> None:
    await bot.send_message(
        chat_id=author.telegram_id,
        text=f"❌ Заявка {submission.code} «{submission.title}» отклонена.\n\nПричина: {reason}",
    )
