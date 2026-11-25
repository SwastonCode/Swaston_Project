"""
Простая математическая CAPTCHA с inline-кнопками (защита от ботов при регистрации).
"""
import random

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def generate_captcha() -> tuple[str, InlineKeyboardMarkup, int]:
    a, b = random.randint(1, 9), random.randint(1, 9)
    correct = a + b

    options = {correct}
    while len(options) < 4:
        options.add(correct + random.randint(-5, 5))
    options = list(options)
    random.shuffle(options)

    buttons = [
        InlineKeyboardButton(text=str(opt), callback_data=f"captcha:{opt}:{correct}")
        for opt in options
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])

    text = f"Подтверди, что ты не бот.\n\n{a} + {b} = ?"
    return text, keyboard, correct
