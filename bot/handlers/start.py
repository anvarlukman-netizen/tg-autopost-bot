from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.config import settings
from bot.keyboards.main_menu import main_menu

router = Router()


def admin_only(message: Message) -> bool:
    return message.from_user and message.from_user.id == settings.ADMIN_ID


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not admin_only(message):
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer(
        "👋 Привет! Я бот для автопостинга в ваши Telegram-каналы.\n\n"
        "Выберите действие:",
        reply_markup=main_menu(),
    )
