from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Предложить исходник")],
        [KeyboardButton(text="📚 Каталог"), KeyboardButton(text="👤 Мой профиль")],
        [KeyboardButton(text="📜 Правила"), KeyboardButton(text="💬 Поддержка")],
    ],
    resize_keyboard=True,
)
