import sqlite3

DB_NAME = "tasks.db"

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_text TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_task_to_db(user_id: int, task_text: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, task_text) VALUES (?, ?)", (user_id, task_text))
    conn.commit()
    conn.close()

def get_tasks_by_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, task_text FROM tasks WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_task_from_db(task_id: int, user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
    conn.commit()
    conn.close()

def update_task_in_db(task_id: int, user_id: int, new_text: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET task_text=? WHERE id=? AND user_id=?", (new_text, task_id, user_id))
    conn.commit()
    conn.close()
