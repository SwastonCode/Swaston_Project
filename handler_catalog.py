"""
Каталог опубликованных исходников: список, фильтры по платформе/языку, сортировка.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from base import async_session
from crud import list_approved_submissions
from models import Platform
from kb_catalog import FILTER_KEYBOARD, pagination_keyboard

router = Router(name="catalog")

# простое in-memory хранилище активных фильтров по пользователю
_user_filters: dict[int, dict] = {}


def _get_filters(user_id: int) -> dict:
    return _user_filters.setdefault(user_id, {"platform": None, "popularity": False, "offset": 0})


async def _render_catalog(user_id: int) -> tuple[str, object]:
    filters = _get_filters(user_id)
    async with async_session() as session:
        items = await list_approved_submissions(
            session,
            platform=filters["platform"],
            order_by_popularity=filters["popularity"],
            limit=11,
            offset=filters["offset"],
        )

    has_more = len(items) > 10
    items = items[:10]

    if not items:
        return "Пока нет проектов по заданным фильтрам.", pagination_keyboard(filters["offset"], False)

    lines = ["📚 <b>Каталог исходников</b>\n"]
    for item in items:
        lines.append(
            f"<b>{item.code}</b> — {item.title}\n"
            f"  {item.platform.value} / {item.language} | 👍 {item.likes_count} 👎 {item.dislikes_count}\n"
        )
    return "\n".join(lines), pagination_keyboard(filters["offset"], has_more)


@router.message(F.text == "📚 Каталог")
async def show_catalog(message: Message) -> None:
    _user_filters.pop(message.from_user.id, None)
    text, keyboard = await _render_catalog(message.from_user.id)
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "catalog:filters")
async def show_filters(callback: CallbackQuery) -> None:
    await callback.message.answer("Выбери фильтр/сортировку:", reply_markup=FILTER_KEYBOARD)
    await callback.answer()


@router.callback_query(F.data.startswith("catalog:platform:"))
async def filter_platform(callback: CallbackQuery) -> None:
    platform_name = callback.data.split(":")[2]
    filters = _get_filters(callback.from_user.id)
    filters["platform"] = Platform[platform_name]
    filters["offset"] = 0

    text, keyboard = await _render_catalog(callback.from_user.id)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer(f"Фильтр: {Platform[platform_name].value}")


@router.callback_query(F.data == "catalog:sort:popularity")
async def sort_popularity(callback: CallbackQuery) -> None:
    filters = _get_filters(callback.from_user.id)
    filters["popularity"] = True
    filters["offset"] = 0
    text, keyboard = await _render_catalog(callback.from_user.id)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer("Сортировка: по популярности")


@router.callback_query(F.data == "catalog:sort:date")
async def sort_date(callback: CallbackQuery) -> None:
    filters = _get_filters(callback.from_user.id)
    filters["popularity"] = False
    filters["offset"] = 0
    text, keyboard = await _render_catalog(callback.from_user.id)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer("Сортировка: по дате")


@router.callback_query(F.data == "catalog:reset")
async def reset_filters(callback: CallbackQuery) -> None:
    _user_filters.pop(callback.from_user.id, None)
    text, keyboard = await _render_catalog(callback.from_user.id)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer("Фильтры сброшены")


@router.callback_query(F.data.startswith("catalog:page:"))
async def change_page(callback: CallbackQuery) -> None:
    offset = int(callback.data.split(":")[2])
    filters = _get_filters(callback.from_user.id)
    filters["offset"] = offset
    text, keyboard = await _render_catalog(callback.from_user.id)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
