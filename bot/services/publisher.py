from aiogram import Bot
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, InputMediaVideo, LinkPreviewOptions,
)

from bot.db.models import MediaType, Post


def _build_reply_markup(post: Post) -> InlineKeyboardMarkup | None:
    if not post.buttons:
        return None
    rows: dict[int, list[InlineKeyboardButton]] = {}
    for btn in sorted(post.buttons, key=lambda b: (b.row, b.col)):
        rows.setdefault(btn.row, []).append(
            InlineKeyboardButton(text=btn.text, url=btn.url)
        )
    return InlineKeyboardMarkup(inline_keyboard=[rows[r] for r in sorted(rows)])


def _build_text(post: Post) -> str:
    parts = []
    if post.text:
        parts.append(post.text)
    if post.footer:
        parts.append(post.footer)
    return "\n\n".join(parts) if parts else ""


async def send_post(bot: Bot, post: Post) -> int:
    channel_id = post.channel.tg_id
    text = _build_text(post)
    markup = _build_reply_markup(post)
    silent = post.silent
    link_preview = LinkPreviewOptions(is_disabled=post.disable_web_preview)

    media = sorted(post.media, key=lambda m: m.position)

    if not media:
        msg = await bot.send_message(
            chat_id=channel_id,
            text=text or "‍",
            parse_mode="HTML",
            reply_markup=markup,
            disable_notification=silent,
            link_preview_options=link_preview,
        )
        return msg.message_id

    if len(media) == 1:
        m = media[0]
        if m.media_type == MediaType.photo:
            msg = await bot.send_photo(
                chat_id=channel_id,
                photo=m.file_id,
                caption=text or None,
                parse_mode="HTML",
                reply_markup=markup,
                disable_notification=silent,
            )
        else:
            msg = await bot.send_video(
                chat_id=channel_id,
                video=m.file_id,
                caption=text or None,
                parse_mode="HTML",
                reply_markup=markup,
                disable_notification=silent,
            )
        return msg.message_id

    # media group — caption only on first item, buttons sent as separate message
    media_list = []
    for i, m in enumerate(media):
        caption = text if i == 0 else None
        if m.media_type == MediaType.photo:
            media_list.append(InputMediaPhoto(media=m.file_id, caption=caption, parse_mode="HTML"))
        else:
            media_list.append(InputMediaVideo(media=m.file_id, caption=caption, parse_mode="HTML"))

    messages = await bot.send_media_group(
        chat_id=channel_id,
        media=media_list,
        disable_notification=silent,
    )
    last_id = messages[-1].message_id

    if markup:
        btn_msg = await bot.send_message(
            chat_id=channel_id,
            text="‍",
            reply_markup=markup,
            disable_notification=True,
        )
        return btn_msg.message_id

    return last_id
