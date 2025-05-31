from aiogram.types import Message
import sqlite3

DB_PATH = "data/tasks.db"

async def delete_task(message: Message):
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("❌ 请使用正确格式：`/delete 任务ID`")
        return

    task_id = int(parts[1])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected:
        await message.answer(f"✅ 成功删除任务 ID {task_id}")
    else:
        await message.answer(f"⚠️ 未找到任务 ID {task_id}")

