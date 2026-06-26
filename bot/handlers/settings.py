from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.db.base import async_session_maker
from bot.db.crud import get_settings, update_settings

router = Router()


class SettingsState(StatesGroup):
    enter_footer = State()
    enter_timezone = State()


def settings_keyboard(s) -> InlineKeyboardMarkup:
    silent_label = "✅ Тихая публикация по умолч." if s.default_silent else "☐ Тихая публикация по умолч."
    footer_label = f"✍️ Подпись: {s.footer[:20]}..." if s.footer and len(s.footer) > 20 else f"✍️ Подпись: {s.footer or 'нет'}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=footer_label, callback_data="set_footer")],
        [InlineKeyboardButton(text=silent_label, callback_data="toggle_default_silent")],
        [InlineKeyboardButton(text=f"🌍 Часовой пояс: {s.timezone}", callback_data="set_timezone")],
    ])


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message) -> None:
    async with async_session_maker() as session:
        s = await get_settings(session)
    await message.answer(
        "⚙️ <b>Глобальные настройки бота:</b>",
        parse_mode="HTML",
        reply_markup=settings_keyboard(s),
    )


@router.callback_query(F.data == "toggle_default_silent")
async def cb_toggle_silent(callback: CallbackQuery) -> None:
    async with async_session_maker() as session:
        s = await get_settings(session)
        await update_settings(session, default_silent=not s.default_silent)
        s = await get_settings(session)
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(s))
    await callback.answer()


@router.callback_query(F.data == "set_footer")
async def cb_set_footer(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "✍️ Введите текст глобальной подписи (будет добавляться к каждому посту).\n"
        "Отправьте <code>-</code> чтобы убрать подпись.",
        parse_mode="HTML",
    )
    await state.set_state(SettingsState.enter_footer)
    await callback.answer()


@router.message(SettingsState.enter_footer, F.text)
async def handle_footer(message: Message, state: FSMContext) -> None:
    footer = None if message.text.strip() == "-" else message.text.strip()
    async with async_session_maker() as session:
        await update_settings(session, footer=footer)
        s = await get_settings(session)
    await message.answer(
        "✅ Подпись обновлена!",
        reply_markup=settings_keyboard(s),
    )
    await state.clear()


@router.callback_query(F.data == "set_timezone")
async def cb_set_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "🌍 Введите часовой пояс (например: <code>Europe/Moscow</code>, <code>Asia/Almaty</code>, <code>UTC</code>):",
        parse_mode="HTML",
    )
    await state.set_state(SettingsState.enter_timezone)
    await callback.answer()


@router.message(SettingsState.enter_timezone, F.text)
async def handle_timezone(message: Message, state: FSMContext) -> None:
    import pytz
    tz_str = message.text.strip()
    if tz_str not in pytz.all_timezones:
        await message.answer(
            f"❌ Неизвестный часовой пояс: <code>{tz_str}</code>\n"
            "Используйте формат: <code>Europe/Moscow</code>",
            parse_mode="HTML",
        )
        return
    async with async_session_maker() as session:
        await update_settings(session, timezone=tz_str)
        s = await get_settings(session)
    await message.answer("✅ Часовой пояс обновлён!", reply_markup=settings_keyboard(s))
    await state.clear()
