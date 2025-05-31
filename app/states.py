from aiogram.fsm.state import StatesGroup, State

class AddTaskState(StatesGroup):
    waiting_for_media = State()
    waiting_for_caption = State()
    waiting_for_buttons = State()
    waiting_for_start_time = State()
    waiting_for_stop_time = State()
    waiting_for_interval = State()
    confirm = State()
