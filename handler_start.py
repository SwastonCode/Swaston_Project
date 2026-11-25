"""
Регистрация пользователя + CAPTCHA + главное меню.
"""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from base import async_session
from crud import get_or_create_user, set_captcha_passed
from kb_main_menu import MAIN_MENU
from captcha import generate_captcha

router = Router(name="start")

# временное хранилище правильных ответов на капчу: {telegram_id: correct_answer}
_pending_captcha: dict[int, int] = {}


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with async_session() as session:
        user, created = await get_or_create_user(
            session, message.from_user.id, message.from_user.username
        )

        if user.captcha_passed:
            await message.answer(
                f"С возвращением, {message.from_user.full_name}!",
                reply_markup=MAIN_MENU,
            )
            return

    text, keyboard, correct = generate_captcha()
    _pending_captcha[message.from_user.id] = correct
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("captcha:"))
async def on_captcha_answer(callback: CallbackQuery) -> None:
    _, chosen, correct = callback.data.split(":")
    chosen, correct = int(chosen), int(correct)

    expected = _pending_captcha.get(callback.from_user.id)
    if expected is None:
        await callback.answer("Капча устарела, напиши /start заново.", show_alert=True)
        return

    if chosen != expected:
        await callback.answer("Неверно, попробуй ещё раз.", show_alert=True)
        return

    _pending_captcha.pop(callback.from_user.id, None)

    async with async_session() as session:
        user, _ = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        await set_captcha_passed(session, user)

    await callback.message.edit_text("✅ Капча пройдена!")
    await callback.message.answer(
        f"Добро пожаловать в Swaston Project, {callback.from_user.full_name}!",
        reply_markup=MAIN_MENU,
    )
    await callback.answer()


@router.message(F.text == "📜 Правила")
async def show_rules(message: Message) -> None:
    await message.answer(
        "📜 <b>Правила платформы</b>\n\n"
        "1. Публикуй только код, на распространение которого у тебя есть право.\n"
        "2. Запрещены вредоносные, пиратские и вредящие пользователям исходники.\n"
        "3. Указывай честное описание проекта.\n"
        "4. Решения модераторов по заявкам окончательные; при несогласии — в поддержку.\n"
        "5. Повторные подозрительные публикации ведут к санкциям вплоть до перманентного бана.",
        parse_mode="HTML",
    )


@router.message(F.text == "💬 Поддержка")
async def show_support(message: Message) -> None:
    await message.answer(
        "💬 По вопросам публикаций и работы бота — опиши проблему прямо здесь, "
        "модераторы отвечают в ближайшее время.\n\n"
        "Для срочных вопросов — обратись к администрации в группе модераторов."
    )
