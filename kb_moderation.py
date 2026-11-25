from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def moderation_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"mod:approve:{submission_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod:reject:{submission_id}"),
            ],
            [
                InlineKeyboardButton(text="🦠 Отметить как вирус", callback_data=f"mod:virus:{submission_id}"),
                InlineKeyboardButton(text="🔨 Выдать наказание", callback_data=f"mod:punish:{submission_id}"),
            ],
        ]
    )


def punish_type_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏱ Часы", callback_data=f"punish_type:hours:{submission_id}")],
            [InlineKeyboardButton(text="📅 Дни", callback_data=f"punish_type:days:{submission_id}")],
            [InlineKeyboardButton(text="⛔ Навсегда", callback_data=f"punish_type:perm:{submission_id}")],
            [InlineKeyboardButton(text="🔓 Снять бан", callback_data=f"punish_type:unban:{submission_id}")],
        ]
    )
