from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo

from bot.db.models import MediaType, Post
from bot.services.publisher import _build_reply_markup, _build_text


async def send_preview(bot: Bot, post: Post, admin_id: int) -> None:
    """Send post preview to admin in private chat."""
    text = _build_text(post)
    markup = _build_reply_markup(post)
    media = sorted(post.media, key=lambda m: m.position)

    header = "👁 <b>Предпросмотр поста:</b>\n\n"

    if not media:
        await bot.send_message(
            chat_id=admin_id,
            text=header + (text or "<i>нет текста</i>"),
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=post.disable_web_preview,
        )
        return

    if len(media) == 1:
        m = media[0]
        caption = (header + text) if text else header
        if m.media_type == MediaType.photo:
            await bot.send_photo(
                chat_id=admin_id,
                photo=m.file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup,
            )
        else:
            await bot.send_video(
                chat_id=admin_id,
                video=m.file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup,
            )
        return

    # media group
    media_list = []
    for i, m in enumerate(media):
        caption = (header + text) if i == 0 else None
        if m.media_type == MediaType.photo:
            media_list.append(InputMediaPhoto(media=m.file_id, caption=caption, parse_mode="HTML"))
        else:
            media_list.append(InputMediaVideo(media=m.file_id, caption=caption, parse_mode="HTML"))

    await bot.send_media_group(chat_id=admin_id, media=media_list)

    if markup:
        await bot.send_message(
            chat_id=admin_id,
            text="☝️ <i>Кнопки под постом:</i>",
            parse_mode="HTML",
            reply_markup=markup,
        )
