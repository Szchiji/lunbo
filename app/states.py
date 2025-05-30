from aiogram.fsm.state import StatesGroup, State

class MessageStates(StatesGroup):
    waiting_for_media = State()
    waiting_for_text = State()
    waiting_for_buttons = State()
    waiting_for_interval = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    confirmation = State()