from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models import Platform

FILTER_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🆕 По дате", callback_data="catalog:sort:date")],
        [InlineKeyboardButton(text="🔥 По популярности", callback_data="catalog:sort:popularity")],
        *[
            [InlineKeyboardButton(text=f"📱 {p.value}", callback_data=f"catalog:platform:{p.name}")]
            for p in Platform
        ],
        [InlineKeyboardButton(text="♻️ Сбросить фильтры", callback_data="catalog:reset")],
    ]
)


def pagination_keyboard(offset: int, has_more: bool) -> InlineKeyboardMarkup:
    buttons = []
    if offset > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"catalog:page:{max(0, offset - 10)}"))
    if has_more:
        buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"catalog:page:{offset + 10}"))
    rows = [buttons] if buttons else []
    rows.append([InlineKeyboardButton(text="🔍 Фильтры", callback_data="catalog:filters")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
