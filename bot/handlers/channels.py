from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.db.base import async_session_maker
from bot.db.crud import create_channel, delete_channel, get_channel_by_tg_id, get_channels
from bot.keyboards.channel_select import channels_manage_keyboard
from bot.keyboards.main_menu import main_menu
from bot.states.post import ChannelAdd

router = Router()


@router.message(F.text == "📢 Мои каналы")
async def show_channels(message: Message) -> None:
    async with async_session_maker() as session:
        channels = await get_channels(session)
    if not channels:
        await message.answer(
            "У вас нет подключённых каналов.\n\n"
            "Чтобы добавить канал:\n"
            "1. Добавьте бота как <b>администратора</b> канала\n"
            "2. Дайте права: Post, Delete, Pin messages\n"
            "3. Нажмите кнопку «Добавить канал» ниже",
            parse_mode="HTML",
            reply_markup=channels_manage_keyboard([]),
        )
    else:
        await message.answer(
            f"📢 <b>Ваши каналы ({len(channels)}):</b>",
            parse_mode="HTML",
            reply_markup=channels_manage_keyboard(channels),
        )


@router.callback_query(F.data == "add_channel")
async def cb_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "📨 Перешлите любое сообщение из канала, который хотите добавить.\n\n"
        "<i>Убедитесь, что бот уже добавлен как администратор этого канала.</i>",
        parse_mode="HTML",
    )
    await state.set_state(ChannelAdd.wait_forward)
    await callback.answer()


@router.message(ChannelAdd.wait_forward)
async def handle_forward(message: Message, state: FSMContext) -> None:
    if not message.forward_from_chat:
        await message.answer("❌ Перешлите сообщение именно из канала (не из группы или личного чата).")
        return

    chat = message.forward_from_chat
    if chat.type != "channel":
        await message.answer("❌ Это не канал. Перешлите сообщение из Telegram-канала.")
        return

    async with async_session_maker() as session:
        existing = await get_channel_by_tg_id(session, chat.id)
        if existing:
            await message.answer(f"⚠️ Канал <b>{chat.title}</b> уже добавлен.", parse_mode="HTML")
            await state.clear()
            return
        channel = await create_channel(session, chat.id, chat.title, chat.username)

    username_str = f"@{channel.username}" if channel.username else "приватный"
    await message.answer(
        f"✅ Канал <b>{channel.title}</b> ({username_str}) успешно добавлен!",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )
    await state.clear()


@router.callback_query(F.data.startswith("del_channel:"))
async def cb_delete_channel(callback: CallbackQuery) -> None:
    channel_id = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        await delete_channel(session, channel_id)
        channels = await get_channels(session)
    await callback.message.edit_reply_markup(reply_markup=channels_manage_keyboard(channels))
    await callback.answer("✅ Канал удалён")


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()
