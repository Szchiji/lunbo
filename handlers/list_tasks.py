from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import sqlite3

DB_PATH = "data/tasks.db"

async def list_tasks(message: Message, state: FSMContext):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, text, start_time, end_time FROM tasks")
        tasks = cursor.fetchall()
        conn.close()

        if not tasks:
            await message.answer("暂无任务。")
            return

        msg = "📋 当前任务列表：\n\n"
        for task in tasks:
            msg += f"🆔 ID: {task[0]}\n📝 内容: {task[1]}\n🕐 开始: {task[2]}\n🕒 结束: {task[3]}\n\n"
        await message.answer(msg)
    except Exception as e:
        await message.answer(f"❌ 获取任务失败：{e}")
