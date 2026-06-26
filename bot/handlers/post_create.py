import asyncio
from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.db.base import async_session_maker
from bot.db.crud import (
    add_media, clear_media, create_post, delete_post, get_channels, get_post,
    get_settings, set_buttons, update_post_footer, update_post_options, update_post_text,
)
from bot.keyboards.channel_select import channel_select_keyboard
from bot.keyboards.post_creation import (
    autodelete_keyboard, buttons_step_keyboard, footer_step_keyboard,
    media_step_keyboard, options_keyboard, text_step_keyboard,
)
from bot.keyboards.preview import preview_keyboard
from bot.services.preview import send_preview
from bot.states.post import PostCreation

router = Router()

# Holds media_group accumulation per user: {user_id: {"post_id": int, "items": [], "task": asyncio.Task}}
_media_buffers: dict[int, dict[str, Any]] = {}
_MEDIA_WAIT = 1.5  # seconds to wait for more items in a media group


# ── Step 1: Channel selection ─────────────────────────────────────────────────

@router.message(F.text == "✍️ Создать пост")
async def cmd_create_post(message: Message, state: FSMContext) -> None:
    async with async_session_maker() as session:
        channels = await get_channels(session)
    if not channels:
        await message.answer("❌ Сначала добавьте хотя бы один канал в разделе «📢 Мои каналы».")
        return
    await message.answer("📢 Выберите канал для публикации:", reply_markup=channel_select_keyboard(channels))
    await state.set_state(PostCreation.select_channel)


@router.callback_query(PostCreation.select_channel, F.data.startswith("channel:"))
async def cb_select_channel(callback: CallbackQuery, state: FSMContext) -> None:
    channel_id = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        post = await create_post(session, channel_id)
    await state.update_data(post_id=post.id, buttons=[], btn_row=0, btn_col=0)
    await callback.message.edit_text(
        "✏️ <b>Шаг 1/5: Текст поста</b>\n\n"
        "Отправьте текст поста. Поддерживается HTML-форматирование:\n"
        "<b>жирный</b>, <i>курсив</i>, <code>код</code>, <a href='https://example.com'>ссылка</a>",
        parse_mode="HTML",
        reply_markup=text_step_keyboard(),
    )
    await state.set_state(PostCreation.enter_text)
    await callback.answer()


# ── Step 2: Text ──────────────────────────────────────────────────────────────

@router.message(PostCreation.enter_text, F.text)
async def handle_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = data["post_id"]
    async with async_session_maker() as session:
        await update_post_text(session, post_id, message.text)
    await _go_to_media_step(message, state)


@router.callback_query(PostCreation.enter_text, F.data == "skip_text")
async def cb_skip_text(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _go_to_media_step(callback.message, state)


async def _go_to_media_step(message: Message, state: FSMContext) -> None:
    await message.answer(
        "🖼 <b>Шаг 2/5: Медиа</b>\n\n"
        "Отправьте фото или видео (можно несколько — они объединятся в альбом).\n"
        "Или пропустите если пост только текстовый.",
        parse_mode="HTML",
        reply_markup=media_step_keyboard(False),
    )
    await state.set_state(PostCreation.add_media)


# ── Step 3: Media ─────────────────────────────────────────────────────────────

@router.message(PostCreation.add_media, F.photo | F.video)
async def handle_media(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = message.from_user.id
    data = await state.get_data()
    post_id = data["post_id"]

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    else:
        file_id = message.video.file_id
        media_type = "video"

    buf = _media_buffers.setdefault(user_id, {"post_id": post_id, "items": [], "task": None})
    buf["items"].append((media_type, file_id))

    # Reset the flush timer
    if buf["task"] and not buf["task"].done():
        buf["task"].cancel()

    async def flush():
        await asyncio.sleep(_MEDIA_WAIT)
        items = _media_buffers.pop(user_id, {}).get("items", [])
        async with async_session_maker() as session:
            await clear_media(session, post_id)
            for pos, (mt, fid) in enumerate(items):
                await add_media(session, post_id, mt, fid, pos)
        count = len(items)
        await bot.send_message(
            message.chat.id,
            f"✅ Добавлено медиафайлов: <b>{count}</b>",
            parse_mode="HTML",
            reply_markup=media_step_keyboard(True),
        )

    buf["task"] = asyncio.create_task(flush())


@router.callback_query(PostCreation.add_media, F.data == "media_done")
async def cb_media_done(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _go_to_buttons_step(callback.message, state)


@router.callback_query(PostCreation.add_media, F.data == "skip_media")
async def cb_skip_media(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _go_to_buttons_step(callback.message, state)


async def _go_to_buttons_step(message: Message, state: FSMContext) -> None:
    await message.answer(
        "🔘 <b>Шаг 3/5: Inline-кнопки</b>\n\n"
        "Введите кнопку в формате:\n"
        "<code>Текст кнопки|https://example.com</code>\n\n"
        "Каждое сообщение = одна кнопка. Используйте «Новая строка» чтобы добавить кнопку в следующую строку.",
        parse_mode="HTML",
        reply_markup=buttons_step_keyboard(False),
    )
    await state.set_state(PostCreation.add_buttons)


# ── Step 4: Buttons ───────────────────────────────────────────────────────────

@router.message(PostCreation.add_buttons, F.text)
async def handle_button_input(message: Message, state: FSMContext) -> None:
    if "|" not in message.text:
        await message.answer("❌ Неверный формат. Используйте: <code>Текст|https://url</code>", parse_mode="HTML")
        return
    parts = message.text.split("|", 1)
    btn_text = parts[0].strip()
    btn_url = parts[1].strip()
    if not btn_url.startswith("http"):
        await message.answer("❌ URL должен начинаться с http:// или https://")
        return

    data = await state.get_data()
    buttons: list[dict] = data.get("buttons", [])
    row = data.get("btn_row", 0)
    col = data.get("btn_col", 0)
    buttons.append({"row": row, "col": col, "text": btn_text, "url": btn_url})
    await state.update_data(buttons=buttons, btn_col=col + 1)

    await message.answer(
        f"✅ Кнопка добавлена: <b>{btn_text}</b>",
        parse_mode="HTML",
        reply_markup=buttons_step_keyboard(True),
    )


@router.callback_query(PostCreation.add_buttons, F.data == "new_btn_row")
async def cb_new_row(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.update_data(btn_row=data.get("btn_row", 0) + 1, btn_col=0)
    await callback.answer("↩ Следующая кнопка будет в новой строке")


@router.callback_query(PostCreation.add_buttons, F.data == "add_btn")
async def cb_add_btn(callback: CallbackQuery) -> None:
    await callback.answer("Введите кнопку в чат в формате: Текст|https://url")


@router.callback_query(PostCreation.add_buttons, F.data.in_({"buttons_done", "skip_buttons"}))
async def cb_buttons_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = data["post_id"]
    buttons = data.get("buttons", [])
    async with async_session_maker() as session:
        await set_buttons(session, post_id, buttons)
        global_settings = await get_settings(session)
    await callback.answer()
    await _go_to_footer_step(callback.message, state, global_settings.footer)


async def _go_to_footer_step(message: Message, state: FSMContext, global_footer: str | None) -> None:
    text = "✍️ <b>Шаг 4/5: Подпись</b>\n\nВведите подпись (footer) для этого поста:"
    if global_footer:
        text += f"\n\n<i>Глобальная подпись:</i> {global_footer}"
    await message.answer(text, parse_mode="HTML", reply_markup=footer_step_keyboard(global_footer))
    await state.set_state(PostCreation.enter_footer)


# ── Step 5: Footer ────────────────────────────────────────────────────────────

@router.message(PostCreation.enter_footer, F.text)
async def handle_footer(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = data["post_id"]
    async with async_session_maker() as session:
        await update_post_footer(session, post_id, message.text)
        global_settings = await get_settings(session)
    await _go_to_options_step(message, state, global_settings.default_silent)


@router.callback_query(PostCreation.enter_footer, F.data == "use_global_footer")
async def cb_use_global_footer(callback: CallbackQuery, state: FSMContext) -> None:
    # footer=None means "use global"
    async with async_session_maker() as session:
        global_settings = await get_settings(session)
    await callback.answer()
    await _go_to_options_step(callback.message, state, global_settings.default_silent)


@router.callback_query(PostCreation.enter_footer, F.data == "skip_footer")
async def cb_skip_footer(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    async with async_session_maker() as session:
        await update_post_footer(session, data["post_id"], None)
        global_settings = await get_settings(session)
    await callback.answer()
    await _go_to_options_step(callback.message, state, global_settings.default_silent)


async def _go_to_options_step(message: Message, state: FSMContext, default_silent: bool) -> None:
    await state.update_data(silent=default_silent, pin=False, auto_delete=None, no_preview=False)
    data = await state.get_data()
    await message.answer(
        "⚙️ <b>Шаг 5/5: Настройки публикации</b>",
        parse_mode="HTML",
        reply_markup=options_keyboard(
            silent=data["silent"],
            pin=data["pin"],
            auto_delete=data["auto_delete"],
            no_preview=data["no_preview"],
        ),
    )
    await state.set_state(PostCreation.set_options)


# ── Step 6: Options ───────────────────────────────────────────────────────────

@router.callback_query(PostCreation.set_options, F.data == "toggle_silent")
async def cb_toggle_silent(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    new_val = not data.get("silent", False)
    await state.update_data(silent=new_val)
    data = await state.get_data()
    await callback.message.edit_reply_markup(
        reply_markup=options_keyboard(data["silent"], data["pin"], data["auto_delete"], data["no_preview"])
    )
    await callback.answer()


@router.callback_query(PostCreation.set_options, F.data == "toggle_pin")
async def cb_toggle_pin(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    new_val = not data.get("pin", False)
    await state.update_data(pin=new_val)
    data = await state.get_data()
    await callback.message.edit_reply_markup(
        reply_markup=options_keyboard(data["silent"], data["pin"], data["auto_delete"], data["no_preview"])
    )
    await callback.answer()


@router.callback_query(PostCreation.set_options, F.data == "toggle_preview")
async def cb_toggle_preview(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    new_val = not data.get("no_preview", False)
    await state.update_data(no_preview=new_val)
    data = await state.get_data()
    await callback.message.edit_reply_markup(
        reply_markup=options_keyboard(data["silent"], data["pin"], data["auto_delete"], data["no_preview"])
    )
    await callback.answer()


@router.callback_query(PostCreation.set_options, F.data == "set_autodelete")
async def cb_set_autodelete(callback: CallbackQuery) -> None:
    await callback.message.answer("⏱ Выберите время автоудаления:", reply_markup=autodelete_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("autodelete:"))
async def cb_autodelete_value(callback: CallbackQuery, state: FSMContext) -> None:
    seconds = int(callback.data.split(":")[1])
    await state.update_data(auto_delete=seconds if seconds > 0 else None)
    data = await state.get_data()
    await callback.message.edit_text(
        "⚙️ <b>Шаг 5/5: Настройки публикации</b>",
        parse_mode="HTML",
        reply_markup=options_keyboard(data["silent"], data["pin"], data["auto_delete"], data["no_preview"]),
    )
    await callback.answer()


@router.callback_query(PostCreation.set_options, F.data == "go_preview")
async def cb_go_preview(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    post_id = data["post_id"]
    async with async_session_maker() as session:
        await update_post_options(
            session, post_id,
            silent=data.get("silent", False),
            pin=data.get("pin", False),
            auto_delete=data.get("auto_delete"),
            disable_web_preview=data.get("no_preview", False),
        )
        post = await get_post(session, post_id)

    await send_preview(bot, post, callback.from_user.id)
    await callback.message.answer(
        "👆 Предпросмотр вашего поста. Что делаем?",
        reply_markup=preview_keyboard(post_id),
    )
    await state.set_state(PostCreation.preview)
    await callback.answer()


# ── Preview actions ───────────────────────────────────────────────────────────

@router.callback_query(PostCreation.preview, F.data.startswith("publish_now:"))
async def cb_publish_now(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    post_id = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        post = await get_post(session, post_id)
        if not post:
            await callback.answer("❌ Пост не найден")
            return
        from bot.services.publisher import send_post
        from bot.db.crud import mark_published, mark_failed
        try:
            msg_id = await send_post(bot, post)
            await mark_published(session, post_id, msg_id)
            if post.pin_after_publish:
                try:
                    await bot.pin_chat_message(post.channel.tg_id, msg_id, disable_notification=True)
                except Exception:
                    pass
        except Exception as e:
            await mark_failed(session, post_id)
            await callback.message.answer(f"❌ Ошибка публикации: <code>{e}</code>", parse_mode="HTML")
            await state.clear()
            await callback.answer()
            return

    await callback.message.answer(f"✅ Пост <b>#{post_id}</b> опубликован!", parse_mode="HTML")
    await state.clear()
    await callback.answer()


@router.callback_query(PostCreation.preview, F.data.startswith("cancel_draft:"))
async def cb_cancel_draft(callback: CallbackQuery, state: FSMContext) -> None:
    post_id = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        await delete_post(session, post_id)
    await callback.message.answer("🗑 Черновик удалён.")
    await state.clear()
    await callback.answer()


@router.callback_query(PostCreation.preview, F.data.startswith("edit_text:"))
async def cb_edit_text(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "✏️ Введите новый текст поста:",
        reply_markup=text_step_keyboard(),
    )
    await state.set_state(PostCreation.enter_text)
    await callback.answer()


@router.callback_query(PostCreation.preview, F.data.startswith("edit_media:"))
async def cb_edit_media(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = data["post_id"]
    async with async_session_maker() as session:
        await clear_media(session, post_id)
    await callback.message.answer(
        "🖼 Отправьте новые фото/видео:",
        reply_markup=media_step_keyboard(False),
    )
    await state.set_state(PostCreation.add_media)
    await callback.answer()


@router.callback_query(PostCreation.preview, F.data.startswith("edit_buttons:"))
async def cb_edit_buttons(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(buttons=[], btn_row=0, btn_col=0)
    await callback.message.answer(
        "🔘 Введите кнопки заново (формат: <code>Текст|https://url</code>):",
        parse_mode="HTML",
        reply_markup=buttons_step_keyboard(False),
    )
    await state.set_state(PostCreation.add_buttons)
    await callback.answer()


@router.callback_query(PostCreation.preview, F.data.startswith("edit_options:"))
async def cb_edit_options(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await callback.message.answer(
        "⚙️ Настройки публикации:",
        reply_markup=options_keyboard(
            data.get("silent", False), data.get("pin", False),
            data.get("auto_delete"), data.get("no_preview", False)
        ),
    )
    await state.set_state(PostCreation.set_options)
    await callback.answer()
