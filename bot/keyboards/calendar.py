import calendar
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def calendar_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    today = date.today()
    rows = []

    # Header: ◀ Июнь 2026 ▶
    rows.append([
        InlineKeyboardButton(text="◀️", callback_data=f"cal:prev:{year}:{month}"),
        InlineKeyboardButton(text=f"{MONTHS_RU[month]} {year}", callback_data="cal:ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal:next:{year}:{month}"),
    ])

    # Days of week
    rows.append([InlineKeyboardButton(text=d, callback_data="cal:ignore") for d in DAYS_RU])

    # Day grid
    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal:ignore"))
            else:
                d = date(year, month, day)
                if d < today:
                    row.append(InlineKeyboardButton(text=f"·{day}·", callback_data="cal:ignore"))
                else:
                    row.append(InlineKeyboardButton(text=str(day), callback_data=f"cal:day:{year}:{month}:{day}"))
        rows.append(row)

    # Shortcuts
    from datetime import timedelta
    tomorrow = today + timedelta(days=1)
    rows.append([
        InlineKeyboardButton(text="📅 Сегодня", callback_data=f"cal:day:{today.year}:{today.month}:{today.day}"),
        InlineKeyboardButton(text="📅 Завтра", callback_data=f"cal:day:{tomorrow.year}:{tomorrow.month}:{tomorrow.day}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def time_keyboard(selected_hour: int | None = None, selected_minute: int | None = None) -> InlineKeyboardMarkup:
    rows = []

    # Hours label
    rows.append([InlineKeyboardButton(text="🕐 Выберите час:", callback_data="cal:ignore")])

    # Hours 0-23, по 6 в строке
    for start in range(0, 24, 6):
        row = []
        for h in range(start, start + 6):
            label = f"[{h:02d}]" if h == selected_hour else f"{h:02d}"
            row.append(InlineKeyboardButton(text=label, callback_data=f"cal:hour:{h}"))
        rows.append(row)

    # Minutes label
    rows.append([InlineKeyboardButton(text="⏱ Выберите минуты:", callback_data="cal:ignore")])

    # Minutes 0, 5, 10 ... 55, по 6 в строке
    minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
    for i in range(0, len(minutes), 6):
        row = []
        for m in minutes[i:i + 6]:
            label = f"[{m:02d}]" if m == selected_minute else f"{m:02d}"
            row.append(InlineKeyboardButton(text=label, callback_data=f"cal:min:{m}"))
        rows.append(row)

    # Confirm button — appears only when both selected
    if selected_hour is not None and selected_minute is not None:
        rows.append([
            InlineKeyboardButton(
                text=f"✅ Подтвердить {selected_hour:02d}:{selected_minute:02d}",
                callback_data="cal:confirm",
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
