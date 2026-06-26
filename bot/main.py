import asyncio
import logging

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

    try:
        logger.info("Bot started polling")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
