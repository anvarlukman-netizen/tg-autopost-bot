from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def text_step_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить (без текста)", callback_data="skip_text")],
    ])


def media_step_keyboard(has_media: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_media:
        rows.append([InlineKeyboardButton(text="✅ Медиа добавлено, продолжить", callback_data="media_done")])
    rows.append([InlineKeyboardButton(text="⏭ Пропустить (без медиа)", callback_data="skip_media")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def buttons_step_keyboard(has_buttons: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_buttons:
        rows.append([InlineKeyboardButton(text="➕ Добавить ещё кнопку", callback_data="add_btn")])
        rows.append([InlineKeyboardButton(text="↩ Новая строка кнопок", callback_data="new_btn_row")])
        rows.append([InlineKeyboardButton(text="✅ Готово с кнопками", callback_data="buttons_done")])
    else:
        rows.append([InlineKeyboardButton(text="➕ Добавить кнопку", callback_data="add_btn")])
        rows.append([InlineKeyboardButton(text="⏭ Пропустить (без кнопок)", callback_data="skip_buttons")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def footer_step_keyboard(global_footer: str | None) -> InlineKeyboardMarkup:
    rows = []
    if global_footer:
        rows.append([InlineKeyboardButton(text=f"✅ Использовать глобальную подпись", callback_data="use_global_footer")])
    rows.append([InlineKeyboardButton(text="🚫 Без подписи", callback_data="skip_footer")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def options_keyboard(silent: bool, pin: bool, auto_delete: int | None, no_preview: bool) -> InlineKeyboardMarkup:
    def toggle(val: bool) -> str:
        return "✅" if val else "☐"

    auto_label = f"🗑 Автоудаление: {auto_delete // 3600}ч" if auto_delete else "🗑 Автоудаление: нет"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{toggle(silent)} Тихая публикация", callback_data="toggle_silent")],
        [InlineKeyboardButton(text=f"{toggle(pin)} Закрепить пост", callback_data="toggle_pin")],
        [InlineKeyboardButton(text=f"{toggle(no_preview)} Без превью ссылок", callback_data="toggle_preview")],
        [InlineKeyboardButton(text=auto_label, callback_data="set_autodelete")],
        [InlineKeyboardButton(text="👁 Предпросмотр →", callback_data="go_preview")],
    ])


def autodelete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1ч", callback_data="autodelete:3600"),
            InlineKeyboardButton(text="3ч", callback_data="autodelete:10800"),
            InlineKeyboardButton(text="6ч", callback_data="autodelete:21600"),
        ],
        [
            InlineKeyboardButton(text="12ч", callback_data="autodelete:43200"),
            InlineKeyboardButton(text="24ч", callback_data="autodelete:86400"),
            InlineKeyboardButton(text="48ч", callback_data="autodelete:172800"),
        ],
        [InlineKeyboardButton(text="❌ Без автоудаления", callback_data="autodelete:0")],
    ])
