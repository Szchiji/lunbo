from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import update_task_in_db, get_tasks_by_user

class EditStates(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_new_task = State()

async def start_edit(message: types.Message, state: FSMContext):
    tasks = get_tasks_by_user(message.from_user.id)
    if not tasks:
        await message.answer("你还没有任何任务。")
        return
    text = "请选择你要编辑的任务编号：\n"
    for task_id, task_text in tasks:
        text += f"{task_id}. {task_text}\n"
    await message.answer(text)
    await message.answer("请输入任务编号：")
    await state.set_state(EditStates.waiting_for_task_id)

async def process_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_state = await state.get_state()
    if current_state == EditStates.waiting_for_task_id:
        if not message.text.isdigit():
            await message.answer("请输入有效的任务编号。")
            return
        task_id = int(message.text)
        tasks = get_tasks_by_user(message.from_user.id)
        task_ids = [t[0] for t in tasks]
        if task_id not in task_ids:
            await message.answer("任务编号不存在，请重新输入。")
            return
        await state.update_data(task_id=task_id)
        await message.answer("请输入新的任务内容：")
        await state.set_state(EditStates.waiting_for_new_task)
    elif current_state == EditStates.waiting_for_new_task:
        new_text = message.text.strip()
        if not new_text:
            await message.answer("任务内容不能为空，请重新输入。")
            return
        data = await state.get_data()
        task_id = data.get("task_id")
        update_task_in_db(task_id, message.from_user.id, new_text)
        await message.answer(f"✅ 任务 {task_id} 已更新为：{new_text}")
        await state.clear()
