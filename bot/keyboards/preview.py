from datetime import datetime

import pytz
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import settings


def _fmt_local(dt: datetime) -> str:
    tz = pytz.timezone(settings.TIMEZONE)
    return pytz.utc.localize(dt).astimezone(tz).strftime("%d.%m %H:%M")


def preview_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Опубликовать сейчас", callback_data=f"publish_now:{post_id}"),
        ],
        [
            InlineKeyboardButton(text="⏰ Запланировать", callback_data=f"schedule:{post_id}"),
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"edit_text:{post_id}"),
            InlineKeyboardButton(text="🖼 Изменить медиа", callback_data=f"edit_media:{post_id}"),
        ],
        [
            InlineKeyboardButton(text="🔘 Изменить кнопки", callback_data=f"edit_buttons:{post_id}"),
            InlineKeyboardButton(text="⚙️ Настройки поста", callback_data=f"edit_options:{post_id}"),
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_draft:{post_id}"),
        ],
    ])


def post_list_keyboard(posts: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    start = page * per_page
    chunk = posts[start:start + per_page]
    rows = []
    for post in chunk:
        dt = _fmt_local(post.scheduled_at) if post.scheduled_at else "—"
        ch_name = post.channel.title if post.channel else "?"
        rows.append([InlineKeyboardButton(
            text=f"#{post.id} | {ch_name} | {dt}",
            callback_data=f"view_post:{post.id}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"posts_page:{page-1}"))
    if start + per_page < len(posts):
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"posts_page:{page+1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_actions_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 Предпросмотр", callback_data=f"preview_post:{post_id}")],
        [InlineKeyboardButton(text="❌ Отменить публикацию", callback_data=f"cancel_post:{post_id}")],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="posts_page:0")],
    ])
