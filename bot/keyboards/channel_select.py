from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.db.models import Channel


def channel_select_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        label = f"📢 {ch.title}" + (f" (@{ch.username})" if ch.username else "")
        rows.append([InlineKeyboardButton(text=label, callback_data=f"channel:{ch.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channels_manage_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        label = f"📢 {ch.title}"
        rows.append([
            InlineKeyboardButton(text=label, callback_data="noop"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_channel:{ch.id}"),
        ])
    rows.append([InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
