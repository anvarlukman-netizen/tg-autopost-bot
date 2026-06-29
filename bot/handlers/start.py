import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.config import settings
from bot.keyboards.main_menu import main_menu

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    logger.info("START from user_id=%s, ADMIN_ID=%s", user_id, settings.ADMIN_ID)
    if not (message.from_user and message.from_user.id == settings.ADMIN_ID):
        await message.answer(
            f"⛔ Нет доступа.\n<code>Ваш ID: {user_id}\nAdmin ID: {settings.ADMIN_ID}</code>",
            parse_mode="HTML",
        )
        return
    await message.answer(
        "👋 Привет! Я бот для автопостинга в ваши Telegram-каналы.\n\n"
        "Выберите действие:",
        reply_markup=main_menu(),
    )


@router.message()
async def debug_catch_all(message: Message) -> None:
    """Temporary: catch all messages to confirm bot receives them."""
    user_id = message.from_user.id if message.from_user else None
    logger.info("MSG from user_id=%s text=%r", user_id, message.text)
    if user_id == settings.ADMIN_ID:
        await message.answer(
            f"✅ Бот получил твоё сообщение: <code>{message.text}</code>",
            parse_mode="HTML",
        )
