import sqlite3
from config import DATABASE_PATH

def add_task(chat_id: int, data: dict):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (chat_id INTEGER, start_time TEXT, end_time TEXT, interval INTEGER, text TEXT, button TEXT)''')
    c.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?)",
              (chat_id, data['start_time'], data['end_time'], data['interval'], data['text'], data.get('button')))
    conn.commit()
    conn.close()