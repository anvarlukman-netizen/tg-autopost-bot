from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✍️ Создать пост"), KeyboardButton(text="📢 Мои каналы")],
            [KeyboardButton(text="📅 Запланированные"), KeyboardButton(text="⚙️ Настройки")],
        ],
        resize_keyboard=True,
    )
