"""
Пошаговая анкета подачи исходника (FSM) + проверка файла перед модерацией.
"""
import json
import os
import uuid

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import config
from base import async_session
from crud import create_submission, get_or_create_user
from models import Platform
from kb_main_menu import MAIN_MENU
from kb_submission import CONFIRM_KEYBOARD, PLATFORM_KEYBOARD, SKIP_KEYBOARD
from notify import send_to_moderation
from validation import validate_archive

router = Router(name="submission")


class SubmissionForm(StatesGroup):
    title = State()
    platform = State()
    language = State()
    version = State()
    description = State()
    license = State()
    github_url = State()
    archive = State()
    screenshots = State()
    confirm = State()


@router.message(F.text == "➕ Предложить исходник")
async def start_submission(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SubmissionForm.title)
    await message.answer(
        "Шаг 1/9. Название проекта:",
        reply_markup=None,
    )


@router.message(StateFilter(SubmissionForm.title))
async def set_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(SubmissionForm.platform)
    await message.answer("Шаг 2/9. Выбери платформу:", reply_markup=PLATFORM_KEYBOARD)


@router.callback_query(StateFilter(SubmissionForm.platform), F.data.startswith("platform:"))
async def set_platform(callback: CallbackQuery, state: FSMContext) -> None:
    _, platform_name = callback.data.split(":")
    await state.update_data(platform=platform_name)
    await state.set_state(SubmissionForm.language)
    await callback.message.edit_text(f"Платформа: {Platform[platform_name].value}")
    await callback.message.answer("Шаг 3/9. Язык программирования:")
    await callback.answer()


@router.message(StateFilter(SubmissionForm.language))
async def set_language(message: Message, state: FSMContext) -> None:
    await state.update_data(language=message.text.strip())
    await state.set_state(SubmissionForm.version)
    await message.answer("Шаг 4/9. Версия проекта (например 1.0):")


@router.message(StateFilter(SubmissionForm.version))
async def set_version(message: Message, state: FSMContext) -> None:
    await state.update_data(version=message.text.strip())
    await state.set_state(SubmissionForm.description)
    await message.answer("Шаг 5/9. Описание проекта:")


@router.message(StateFilter(SubmissionForm.description))
async def set_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(SubmissionForm.license)
    await message.answer("Шаг 6/9. Лицензия (необязательно):", reply_markup=SKIP_KEYBOARD)


@router.message(StateFilter(SubmissionForm.license))
async def set_license(message: Message, state: FSMContext) -> None:
    await state.update_data(license=message.text.strip())
    await _ask_github(message, state)


@router.callback_query(StateFilter(SubmissionForm.license), F.data == "skip")
async def skip_license(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(license=None)
    await callback.message.edit_text("Лицензия: пропущено")
    await _ask_github(callback.message, state)
    await callback.answer()


async def _ask_github(message: Message, state: FSMContext) -> None:
    await state.set_state(SubmissionForm.github_url)
    await message.answer("Шаг 7/9. Ссылка на GitHub (необязательно):", reply_markup=SKIP_KEYBOARD)


@router.message(StateFilter(SubmissionForm.github_url))
async def set_github(message: Message, state: FSMContext) -> None:
    await state.update_data(github_url=message.text.strip())
    await _ask_archive(message, state)


@router.callback_query(StateFilter(SubmissionForm.github_url), F.data == "skip")
async def skip_github(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(github_url=None)
    await callback.message.edit_text("GitHub: пропущено")
    await _ask_archive(callback.message, state)
    await callback.answer()


async def _ask_archive(message: Message, state: FSMContext) -> None:
    await state.set_state(SubmissionForm.archive)
    await message.answer(f"Шаг 8/9. Пришли архив с исходным кодом (.zip, до {config.MAX_ARCHIVE_SIZE_MB}MB):")


@router.message(StateFilter(SubmissionForm.archive), F.document)
async def set_archive(message: Message, state: FSMContext, bot: Bot) -> None:
    document = message.document
    filename = document.file_name or "archive.zip"

    os.makedirs(config.STORAGE_DIR, exist_ok=True)
    temp_path = os.path.join(config.STORAGE_DIR, f"{uuid.uuid4().hex}_{filename}")
    await bot.download(document.file_id, destination=temp_path)

    result = validate_archive(temp_path, filename)
    os.remove(temp_path)  # исходники не хранятся локально дольше проверки; архив живёт в Telegram по file_id

    if not result.ok:
        await message.answer(
            "❌ Архив не прошёл автоматическую проверку:\n" + "\n".join(f"• {r}" for r in result.reasons) +
            "\n\nИсправь архив и пришли заново."
        )
        return

    await state.update_data(
        archive_file_id=document.file_id,
        archive_filename=filename,
        scan_result=result.scan_summary,
    )
    await state.set_state(SubmissionForm.screenshots)
    await message.answer(
        "✅ Архив прошёл проверку.\n\nШаг 9/9. Пришли скриншоты (необязательно, можно несколько, "
        "последним сообщением напиши «готово»):",
        reply_markup=SKIP_KEYBOARD,
    )


@router.message(StateFilter(SubmissionForm.archive))
async def archive_wrong_type(message: Message) -> None:
    await message.answer("Нужен файл-документ с архивом (.zip), не текст и не фото.")


@router.message(StateFilter(SubmissionForm.screenshots), F.photo)
async def add_screenshot(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    screenshots = data.get("screenshots", [])
    screenshots.append(message.photo[-1].file_id)
    await state.update_data(screenshots=screenshots)
    await message.answer(f"Скриншот добавлен ({len(screenshots)}). Пришли ещё или напиши «готово».")


@router.message(StateFilter(SubmissionForm.screenshots), F.text.lower() == "готово")
async def finish_screenshots(message: Message, state: FSMContext) -> None:
    await _show_confirmation(message, state)


@router.callback_query(StateFilter(SubmissionForm.screenshots), F.data == "skip")
async def skip_screenshots(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Скриншоты: пропущено")
    await _show_confirmation(callback.message, state)
    await callback.answer()


async def _show_confirmation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(SubmissionForm.confirm)
    screenshots_count = len(data.get("screenshots", []))
    text = (
        "📋 <b>Проверь заявку перед отправкой:</b>\n\n"
        f"<b>Название:</b> {data['title']}\n"
        f"<b>Платформа:</b> {Platform[data['platform']].value}\n"
        f"<b>Язык:</b> {data['language']}\n"
        f"<b>Версия:</b> {data['version']}\n"
        f"<b>Описание:</b> {data['description']}\n"
        f"<b>Лицензия:</b> {data.get('license') or '—'}\n"
        f"<b>GitHub:</b> {data.get('github_url') or '—'}\n"
        f"<b>Скриншотов:</b> {screenshots_count}\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=CONFIRM_KEYBOARD)


@router.callback_query(StateFilter(SubmissionForm.confirm), F.data == "submit:cancel")
async def cancel_submission(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Заявка отменена.")
    await callback.message.answer("Главное меню:", reply_markup=MAIN_MENU)
    await callback.answer()


@router.callback_query(StateFilter(SubmissionForm.confirm), F.data == "submit:confirm")
async def confirm_submission(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()

    async with async_session() as session:
        user, _ = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)

        submission = await create_submission(
            session,
            user_id=user.id,
            title=data["title"],
            platform=Platform[data["platform"]],
            language=data["language"],
            version=data["version"],
            description=data["description"],
            license=data.get("license"),
            github_url=data.get("github_url"),
            archive_file_id=data["archive_file_id"],
            archive_filename=data["archive_filename"],
            screenshots_json=json.dumps(data.get("screenshots", [])),
            scan_result=data.get("scan_result"),
        )

        await send_to_moderation(bot, submission, user)

    await state.clear()
    await callback.message.edit_text(f"✅ Заявка отправлена на проверку!\nНомер заявки: {submission.code}")
    await callback.message.answer("Главное меню:", reply_markup=MAIN_MENU)
    await callback.answer()
