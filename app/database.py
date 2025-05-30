import sqlite3
from app.config import DATABASE_PATH

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        run_time TEXT NOT NULL,
        message TEXT NOT NULL,
        job_id TEXT UNIQUE NOT NULL,
        file_id TEXT,
        file_type TEXT,
        button_text TEXT,
        button_url TEXT,
        interval_seconds INTEGER,
        start_time TEXT,
        stop_time TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_task(chat_id, run_time, message, job_id, file_id=None, file_type=None,
             button_text=None, button_url=None, interval_seconds=None,
             start_time=None, stop_time=None):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tasks (chat_id, run_time, message, job_id, file_id, file_type, button_text, button_url, interval_seconds, start_time, stop_time)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (chat_id, run_time, message, job_id, file_id, file_type, button_text, button_url, interval_seconds, start_time, stop_time))
    conn.commit()
    conn.close()

def get_all_tasks(chat_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE chat_id = ?", (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_task(job_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE job_id = ?", (job_id,))
    conn.commit()
    conn.close()