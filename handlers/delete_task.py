from aiogram import types
from database import delete_task_from_db, get_tasks_by_user

async def delete_task(message: types.Message):
    args = message.get_args()
    if not args.isdigit():
        await message.answer("请在命令后面跟上要删除的任务编号，例如 /delete 2")
        return
    task_id = int(args)
    tasks = get_tasks_by_user(message.from_user.id)
    task_ids = [t[0] for t in tasks]
    if task_id not in task_ids:
        await message.answer(f"任务编号 {task_id} 不存在。")
        return
    delete_task_from_db(task_id, message.from_user.id)
    await message.answer(f"✅ 任务 {task_id} 已删除。")

