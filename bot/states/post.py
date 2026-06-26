from aiogram.fsm.state import State, StatesGroup


class PostCreation(StatesGroup):
    select_channel = State()
    enter_text = State()
    add_media = State()
    add_buttons = State()
    enter_footer = State()
    set_options = State()
    preview = State()


class PostSchedule(StatesGroup):
    enter_date = State()
    enter_time = State()


class ChannelAdd(StatesGroup):
    wait_forward = State()
