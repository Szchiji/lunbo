from aiogram import types
from database import get_tasks_by_user

async def list_tasks(message: types.Message):
    tasks = get_tasks_by_user(message.from_user.id)
    if not tasks:
        await message.answer("你还没有任何任务。")
        return
    text = "你的任务列表：\n"
    for task_id, task_text in tasks:
        text += f"{task_id}. {task_text}\n"
    await message.answer(text)
