import sqlite3
from datetime import datetime

conn = sqlite3.connect("tasks.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    user_id INTEGER,
    scheduled_time TEXT,
    message TEXT,
    job_id TEXT PRIMARY KEY
)
""")
conn.commit()

def add_task(user_id, scheduled_time: datetime, message, job_id):
    cursor.execute(
        "INSERT INTO tasks VALUES (?, ?, ?, ?)",
        (user_id, scheduled_time.isoformat(), message, job_id)
    )
    conn.commit()

def get_all_tasks(user_id):
    cursor.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

def delete_task(job_id):
    cursor.execute("DELETE FROM tasks WHERE job_id = ?", (job_id,))
    conn.commit()