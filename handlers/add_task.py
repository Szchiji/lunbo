from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import add_task_to_db

class TaskStates(StatesGroup):
    waiting_for_task = State()

async def start(message: types.Message, state: FSMContext):
    await message.answer("请输入你要添加的任务内容：")
    await state.set_state(TaskStates.waiting_for_task)

async def process_task(message: types.Message, state: FSMContext):
    task_text = message.text.strip()
    if not task_text:
        await message.answer("任务内容不能为空，请重新输入。")
        return
    add_task_to_db(message.from_user.id, task_text)
    await message.answer(f"✅ 任务已添加：{task_text}")
    await state.clear()

