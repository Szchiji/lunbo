import sqlite3

def create_tables():
    with sqlite3.connect("tasks.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                media_type TEXT,
                media_path TEXT,
                caption TEXT,
                buttons TEXT,
                start_time TEXT,
                stop_time TEXT,
                interval INTEGER
            )
        """)

def add_task(data: dict):
    with sqlite3.connect("tasks.db") as conn:
        conn.execute("""
            INSERT INTO tasks (chat_id, media_type, media_path, caption, buttons, start_time, stop_time, interval)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["chat_id"], data["media_type"], data["media_path"], data["caption"],
            data["buttons"], data["start_time"], data["stop_time"], data["interval"]
        ))

def get_tasks():
    with sqlite3.connect("tasks.db") as conn:
        return conn.execute("SELECT * FROM tasks").fetchall()

def delete_task(task_id: int):
    with sqlite3.connect("tasks.db") as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

def update_task(task_id: int, field: str, value):
    with sqlite3.connect("tasks.db") as conn:
        conn.execute(f"UPDATE tasks SET {field} = ? WHERE id = ?", (value, task_id))
