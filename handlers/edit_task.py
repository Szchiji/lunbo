import sqlite3
from fastapi import APIRouter, HTTPException

router = APIRouter()

DATABASE = 'tasks.db'  # 根据你实际数据库路径修改

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@router.put("/tasks/{task_id}")
async def edit_task(task_id: int, content: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 检查任务是否存在
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    # 更新任务内容
    cursor.execute("UPDATE tasks SET content = ? WHERE id = ?", (content, task_id))
    conn.commit()
    conn.close()
    return {"message": "Task updated successfully", "task_id": task_id, "new_content": content}
