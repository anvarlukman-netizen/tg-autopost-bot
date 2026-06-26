import pytz
from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.db.base import async_session_maker
from bot.db.crud import cancel_post, get_post, get_scheduled_posts
from bot.keyboards.preview import post_actions_keyboard, post_list_keyboard
from bot.scheduler.setup import get_scheduler
from bot.services.preview import send_preview


def _to_local_str(dt) -> str:
    tz = pytz.timezone(settings.TIMEZONE)
    return pytz.utc.localize(dt).astimezone(tz).strftime("%d.%m.%Y в %H:%M")

router = Router()


@router.message(F.text == "📅 Запланированные")
async def show_scheduled(message: Message) -> None:
    async with async_session_maker() as session:
        posts = await get_scheduled_posts(session)
    if not posts:
        await message.answer("📭 Нет запланированных постов.")
        return
    await message.answer(
        f"📅 <b>Запланированные посты ({len(posts)}):</b>",
        parse_mode="HTML",
        reply_markup=post_list_keyboard(posts, page=0),
    )


@router.callback_query(F.data.startswith("posts_page:"))
async def cb_posts_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        posts = await get_scheduled_posts(session)
    if not posts:
        await callback.message.edit_text("📭 Нет запланированных постов.")
        await callback.answer()
        return
    await callback.message.edit_reply_markup(reply_markup=post_list_keyboard(posts, page=page))
    await callback.answer()


@router.callback_query(F.data.startswith("view_post:"))
async def cb_view_post(callback: CallbackQuery) -> None:
    post_id = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        post = await get_post(session, post_id)
    if not post:
        await callback.answer("❌ Пост не найден")
        return
    dt = _to_local_str(post.scheduled_at) if post.scheduled_at else "—"
    await callback.message.answer(
        f"📋 <b>Пост #{post_id}</b>\n"
        f"📢 Канал: {post.channel.title}\n"
        f"📅 Дата: {dt}\n"
        f"🔇 Тихо: {'да' if post.silent else 'нет'}\n"
        f"📌 Закрепить: {'да' if post.pin_after_publish else 'нет'}",
        parse_mode="HTML",
        reply_markup=post_actions_keyboard(post_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("preview_post:"))
async def cb_preview_post(callback: CallbackQuery, bot: Bot) -> None:
    post_id = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        post = await get_post(session, post_id)
    if not post:
        await callback.answer("❌ Пост не найден")
        return
    await send_preview(bot, post, settings.ADMIN_ID)
    await callback.answer("👁 Предпросмотр отправлен")


@router.callback_query(F.data.startswith("cancel_post:"))
async def cb_cancel_post(callback: CallbackQuery) -> None:
    post_id = int(callback.data.split(":")[1])
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(f"post_{post_id}")
    except Exception:
        pass
    async with async_session_maker() as session:
        await cancel_post(session, post_id)
    await callback.message.edit_text(f"❌ Пост <b>#{post_id}</b> отменён.", parse_mode="HTML")
    await callback.answer()
