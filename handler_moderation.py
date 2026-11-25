"""
Действия модераторов: подтверждение/отклонение заявок, отметки о вирусах, наказания.
"""
from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

import config
from base import async_session
from crud import (
    add_virus_report,
    apply_sanction,
    get_or_create_user,
    get_submission,
    log_action,
    set_submission_status,
)
from models import SanctionType, SubmissionStatus, User
from kb_moderation import punish_type_keyboard
from notify import notify_author_approved, notify_author_rejected
from publishing import publish_submission
from roles import is_moderator
from sanctions import calc_expiry_days, calc_expiry_hours

router = Router(name="moderation")


class RejectForm(StatesGroup):
    reason = State()


class PunishForm(StatesGroup):
    amount = State()
    reason = State()


def _in_mod_group(callback: CallbackQuery) -> bool:
    return callback.message.chat.id == config.MOD_GROUP_ID


async def _require_moderator(callback: CallbackQuery) -> User | None:
    if not _in_mod_group(callback):
        await callback.answer("Доступно только в группе модераторов.", show_alert=True)
        return None
    async with async_session() as session:
        moderator, _ = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        if not is_moderator(moderator.role):
            await callback.answer("У тебя нет прав модератора.", show_alert=True)
            return None
        return moderator


# --- Подтвердить ---

@router.callback_query(F.data.startswith("mod:approve:"))
async def approve_submission(callback: CallbackQuery, bot: Bot) -> None:
    moderator = await _require_moderator(callback)
    if moderator is None:
        return

    submission_id = int(callback.data.split(":")[2])

    async with async_session() as session:
        submission = await get_submission(session, submission_id)
        if submission is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return
        if submission.status != SubmissionStatus.PENDING:
            await callback.answer("Заявка уже обработана.", show_alert=True)
            return

        await set_submission_status(session, submission, SubmissionStatus.APPROVED, moderator.id)
        author = await session.get(User, submission.user_id)

        await publish_submission(bot, submission)
        await notify_author_approved(bot, author, submission)
        await log_action(session, moderator.id, "approve", "submission", submission.id)

    await callback.message.edit_text(callback.message.text + f"\n\n✅ Подтверждено модератором @{callback.from_user.username}")
    await callback.answer("Заявка одобрена и опубликована.")


# --- Отклонить (запрашиваем причину) ---

@router.callback_query(F.data.startswith("mod:reject:"))
async def start_reject(callback: CallbackQuery, state: FSMContext) -> None:
    moderator = await _require_moderator(callback)
    if moderator is None:
        return

    submission_id = int(callback.data.split(":")[2])
    await state.update_data(submission_id=submission_id)
    await state.set_state(RejectForm.reason)
    await callback.message.reply("Укажи причину отклонения (следующим сообщением):")
    await callback.answer()


@router.message(StateFilter(RejectForm.reason))
async def finish_reject(message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    submission_id = data["submission_id"]
    reason = message.text.strip()
    await state.clear()

    async with async_session() as session:
        moderator, _ = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        submission = await get_submission(session, submission_id)
        if submission is None:
            await message.reply("Заявка не найдена.")
            return
        if submission.status != SubmissionStatus.PENDING:
            await message.reply("Заявка уже обработана.")
            return

        await set_submission_status(session, submission, SubmissionStatus.REJECTED, moderator.id, reason)
        author = await session.get(User, submission.user_id)

        await notify_author_rejected(bot, author, submission, reason)
        await log_action(session, moderator.id, "reject", "submission", submission.id, reason)

    await message.reply(f"❌ Заявка {submission_id} отклонена. Причина передана автору.")


# --- Отметить как вирус ---

@router.callback_query(F.data.startswith("mod:virus:"))
async def mark_virus(callback: CallbackQuery) -> None:
    moderator = await _require_moderator(callback)
    if moderator is None:
        return

    submission_id = int(callback.data.split(":")[2])

    async with async_session() as session:
        submission = await get_submission(session, submission_id)
        if submission is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        added = await add_virus_report(session, submission, moderator)
        if not added:
            await callback.answer("Ты уже отмечал эту заявку.", show_alert=True)
            return

        author = await session.get(User, submission.user_id)
        await log_action(session, moderator.id, "virus_mark", "submission", submission.id)

        if author.virus_marks_count >= config.VIRUS_MARKS_THRESHOLD and author.virus_marks_count % config.VIRUS_MARKS_THRESHOLD == 0:
            author_line = f"@{author.username}" if author.username else f"id{author.telegram_id}"
            await callback.bot.send_message(
                chat_id=config.MOD_GROUP_ID,
                text=(
                    f"⚠️ В пользователе {author_line} было замечено {author.virus_marks_count} "
                    f"случаев подозрительных исходников.\nРекомендуем рассмотреть применение наказания.\n\n"
                    f"Это не является автоматическим доказательством наличия вируса — "
                    f"решение о наказании принимает модератор вручную."
                ),
            )

    await callback.answer("Отметка добавлена.")


# --- Выдать наказание ---

@router.callback_query(F.data.startswith("mod:punish:"))
async def start_punish(callback: CallbackQuery) -> None:
    moderator = await _require_moderator(callback)
    if moderator is None:
        return

    submission_id = int(callback.data.split(":")[2])
    await callback.message.reply("Выбери тип наказания:", reply_markup=punish_type_keyboard(submission_id))
    await callback.answer()


@router.callback_query(F.data.startswith("punish_type:"))
async def choose_punish_type(callback: CallbackQuery, state: FSMContext) -> None:
    moderator = await _require_moderator(callback)
    if moderator is None:
        return

    _, punish_kind, submission_id = callback.data.split(":")
    submission_id = int(submission_id)

    if punish_kind == "unban":
        await _apply_and_report(callback, state, submission_id, SanctionType.UNBAN, None)
        return

    await state.update_data(submission_id=submission_id, punish_kind=punish_kind)
    await state.set_state(PunishForm.amount)

    if punish_kind == "perm":
        await state.update_data(amount=None)
        await state.set_state(PunishForm.reason)
        await callback.message.reply("Укажи причину перманентного бана:")
    else:
        unit = "часов" if punish_kind == "hours" else "дней"
        await callback.message.reply(f"На сколько {unit}? (число)")
    await callback.answer()


@router.message(StateFilter(PunishForm.amount))
async def set_punish_amount(message, state: FSMContext) -> None:
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.reply("Нужно число. Попробуй ещё раз:")
        return
    await state.update_data(amount=amount)
    await state.set_state(PunishForm.reason)
    await message.reply("Укажи причину наказания:")


@router.message(StateFilter(PunishForm.reason))
async def set_punish_reason(message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    reason = message.text.strip()
    punish_kind = data["punish_kind"]
    amount = data.get("amount")
    submission_id = data["submission_id"]

    sanction_type = {
        "hours": SanctionType.TEMP_HOURS,
        "days": SanctionType.TEMP_DAYS,
        "perm": SanctionType.PERMANENT,
    }[punish_kind]

    expires_at = None
    if sanction_type == SanctionType.TEMP_HOURS:
        expires_at = calc_expiry_hours(amount)
    elif sanction_type == SanctionType.TEMP_DAYS:
        expires_at = calc_expiry_days(amount)

    async with async_session() as session:
        moderator, _ = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        submission = await get_submission(session, submission_id)
        author = await session.get(User, submission.user_id)

        await apply_sanction(session, author, moderator, sanction_type, reason, expires_at)
        await log_action(session, moderator.id, f"sanction:{sanction_type.value}", "user", author.id, reason)

        try:
            await bot.send_message(
                chat_id=author.telegram_id,
                text=f"🔨 Тебе выдано наказание: {sanction_type.value}.\nПричина: {reason}",
            )
        except Exception:
            pass  # пользователь мог заблокировать бота

    await state.clear()
    await message.reply("Наказание применено и сохранено в базе.")


async def _apply_and_report(callback: CallbackQuery, state: FSMContext, submission_id: int, sanction_type: SanctionType, reason: str | None) -> None:
    async with async_session() as session:
        moderator, _ = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        submission = await get_submission(session, submission_id)
        author = await session.get(User, submission.user_id)

        await apply_sanction(session, author, moderator, sanction_type, reason or "—", None)
        await log_action(session, moderator.id, f"sanction:{sanction_type.value}", "user", author.id, reason)

    await callback.message.reply("Готово.")
