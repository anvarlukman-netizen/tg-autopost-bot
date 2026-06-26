from datetime import date, datetime

import pytz
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.config import settings
from bot.db.base import async_session_maker
from bot.db.crud import schedule_post
from bot.keyboards.calendar import calendar_keyboard, time_keyboard
from bot.scheduler.jobs import publish_post
from bot.scheduler.setup import get_scheduler
from bot.states.post import PostCreation, PostSchedule

router = Router()


@router.callback_query(PostCreation.preview, F.data.startswith("schedule:"))
async def cb_open_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    post_id = int(callback.data.split(":")[1])
    await state.update_data(scheduling_post_id=post_id)

    tz = pytz.timezone(settings.TIMEZONE)
    now = datetime.now(tz)

    await callback.message.answer(
        f"📅 <b>Выберите дату публикации</b>\n"
        f"<i>Часовой пояс: {settings.TIMEZONE}</i>",
        parse_mode="HTML",
        reply_markup=calendar_keyboard(now.year, now.month),
    )
    await state.set_state(PostSchedule.enter_date)
    await callback.answer()


@router.callback_query(PostSchedule.enter_date, F.data.startswith("cal:"))
async def handle_calendar_click(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    action = parts[1]

    if action == "ignore":
        await callback.answer()
        return

    # Navigate months
    if action in ("prev", "next"):
        year, month = int(parts[2]), int(parts[3])
        if action == "prev":
            month -= 1
            if month < 1:
                month, year = 12, year - 1
        else:
            month += 1
            if month > 12:
                month, year = 1, year + 1
        await callback.message.edit_reply_markup(reply_markup=calendar_keyboard(year, month))
        await callback.answer()
        return

    # Day selected
    if action == "day":
        year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
        selected = date(year, month, day)
        if selected < date.today():
            await callback.answer("❌ Нельзя выбрать прошедшую дату", show_alert=True)
            return

        await state.update_data(sched_date=selected.isoformat(), sched_hour=None, sched_minute=None)
        date_str = selected.strftime("%d.%m.%Y")
        await callback.message.edit_text(
            f"📅 Дата: <b>{date_str}</b>\n\n⏰ <b>Выберите время публикации:</b>",
            parse_mode="HTML",
            reply_markup=time_keyboard(),
        )
        await state.set_state(PostSchedule.enter_time)
        await callback.answer()


@router.callback_query(PostSchedule.enter_time, F.data.startswith("cal:"))
async def handle_time_click(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    action = parts[1]

    if action == "ignore":
        await callback.answer()
        return

    data = await state.get_data()

    if action == "hour":
        hour = int(parts[2])
        await state.update_data(sched_hour=hour)
        data = await state.get_data()
        await callback.message.edit_reply_markup(
            reply_markup=time_keyboard(selected_hour=hour, selected_minute=data.get("sched_minute"))
        )
        await callback.answer(f"Час: {hour:02d}")
        return

    if action == "min":
        minute = int(parts[2])
        await state.update_data(sched_minute=minute)
        data = await state.get_data()
        await callback.message.edit_reply_markup(
            reply_markup=time_keyboard(selected_hour=data.get("sched_hour"), selected_minute=minute)
        )
        await callback.answer(f"Минуты: {minute:02d}")
        return

    if action == "confirm":
        hour = data.get("sched_hour")
        minute = data.get("sched_minute")

        if hour is None or minute is None:
            await callback.answer("❌ Выберите час и минуты", show_alert=True)
            return

        sched_date = date.fromisoformat(data["sched_date"])
        tz = pytz.timezone(settings.TIMEZONE)
        local_dt = tz.localize(datetime(sched_date.year, sched_date.month, sched_date.day, hour, minute))
        utc_dt = local_dt.astimezone(pytz.utc).replace(tzinfo=None)

        if utc_dt <= datetime.utcnow():
            await callback.answer("❌ Это время уже прошло, выберите другое", show_alert=True)
            return

        post_id = data["scheduling_post_id"]
        async with async_session_maker() as session:
            await schedule_post(session, post_id, utc_dt)

        scheduler = get_scheduler()
        scheduler.add_job(
            publish_post,
            trigger="date",
            run_date=utc_dt,
            args=[post_id],
            id=f"post_{post_id}",
            replace_existing=True,
        )

        local_str = local_dt.strftime("%d.%m.%Y в %H:%M")
        await callback.message.edit_text(
            f"✅ Пост <b>#{post_id}</b> запланирован на <b>{local_str}</b> ({settings.TIMEZONE})",
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
