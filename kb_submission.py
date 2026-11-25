from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models import Platform

PLATFORM_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=p.value, callback_data=f"platform:{p.name}")]
        for p in Platform
    ]
)

SKIP_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")]]
)

CONFIRM_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить на модерацию", callback_data="submit:confirm"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="submit:cancel"),
        ]
    ]
)
