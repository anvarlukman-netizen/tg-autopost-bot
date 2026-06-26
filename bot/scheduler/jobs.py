import logging
from datetime import datetime, timedelta

from bot.bot_instance import get_bot
from bot.config import settings
from bot.db.base import async_session_maker
from bot.db.crud import get_post, mark_failed, mark_published
from bot.db.models import PostStatus
from bot.services.publisher import send_post

logger = logging.getLogger(__name__)


async def publish_post(post_id: int) -> None:
    bot = get_bot()
    async with async_session_maker() as session:
        post = await get_post(session, post_id)
        if post is None or post.status != PostStatus.scheduled:
            return

        try:
            message_id = await send_post(bot, post)
            await mark_published(session, post_id, message_id)

            if post.pin_after_publish and message_id:
                try:
                    await bot.pin_chat_message(
                        chat_id=post.channel.tg_id,
                        message_id=message_id,
                        disable_notification=True,
                    )
                except Exception:
                    pass

            if post.auto_delete_after and message_id:
                from bot.scheduler.setup import get_scheduler
                scheduler = get_scheduler()
                delete_at = datetime.utcnow() + timedelta(seconds=post.auto_delete_after)
                scheduler.add_job(
                    auto_delete_post,
                    trigger="date",
                    run_date=delete_at,
                    args=[post_id, post.channel.tg_id, message_id],
                    id=f"delete_{post_id}",
                    replace_existing=True,
                )

            await bot.send_message(
                settings.ADMIN_ID,
                f"✅ Пост <b>#{post_id}</b> опубликован в <b>{post.channel.title}</b>",
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error("Failed to publish post %d: %s", post_id, e)
            await mark_failed(session, post_id)
            await bot.send_message(
                settings.ADMIN_ID,
                f"❌ Ошибка публикации поста <b>#{post_id}</b>:\n<code>{e}</code>",
                parse_mode="HTML",
            )


async def auto_delete_post(post_id: int, channel_tg_id: int, message_id: int) -> None:
    bot = get_bot()
    try:
        await bot.delete_message(chat_id=channel_tg_id, message_id=message_id)
        await bot.send_message(
            settings.ADMIN_ID,
            f"🗑 Пост <b>#{post_id}</b> автоматически удалён из канала",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Failed to delete post %d message: %s", post_id, e)
