import asyncio
import logging
import os

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.bot_instance import set_bot
from bot.config import settings
from bot.db.base import init_db
from bot.handlers import channels, post_create, post_list, post_schedule, settings as settings_handler, start
from bot.scheduler.setup import create_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def run_web_server() -> None:
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health server on port %d", port)


async def self_ping(url: str) -> None:
    try:
        async with aiohttp.ClientSession() as session:
            await session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=10))
        logger.debug("Self-ping OK")
    except Exception as e:
        logger.warning("Self-ping failed: %s", e)


async def main() -> None:
    await init_db()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    set_bot(bot)

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(channels.router)
    dp.include_router(post_create.router)
    dp.include_router(post_schedule.router)
    dp.include_router(post_list.router)
    dp.include_router(settings_handler.router)

    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    # Keep Render free tier awake by pinging own URL every 14 minutes
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        scheduler.add_job(self_ping, "interval", minutes=14, args=[render_url], id="self_ping")
        logger.info("Self-ping enabled for %s", render_url)

    await run_web_server()

    try:
        logger.info("Bot started polling")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
