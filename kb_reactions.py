from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def reactions_keyboard(submission_id: int, likes: int, dislikes: int, discuss_url: str | None = None) -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(text=f"👍 {likes}", callback_data=f"react:like:{submission_id}"),
        InlineKeyboardButton(text=f"👎 {dislikes}", callback_data=f"react:dislike:{submission_id}"),
    ]
    rows = [row]
    if discuss_url:
        rows.append([InlineKeyboardButton(text="💬 Обсудить", url=discuss_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
