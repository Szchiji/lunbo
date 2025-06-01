import sqlite3
from contextlib import closing

DB_PATH = 'tasks.db'

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    content TEXT,
                    message_type TEXT,
                    file_path TEXT,
                    buttons TEXT,
                    interval INTEGER,
                    start_time TEXT,
                    end_time TEXT
                )
            ''')

def add_schedule(task):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            cursor = conn.execute('''
                INSERT INTO schedules
                (chat_id, content, message_type, file_path, buttons, interval, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task['chat_id'],
                task.get('content'),
                task.get('message_type'),
                task.get('file_path'),
                task.get('buttons'),
                task.get('interval'),
                task.get('start_time'),
                task.get('end_time')
            ))
            return cursor.lastrowid

def get_schedule(task_id):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.execute('SELECT * FROM schedules WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if row:
            keys = ['id', 'chat_id', 'content', 'message_type', 'file_path', 'buttons', 'interval', 'start_time', 'end_time']
            return dict(zip(keys, row))
        return None

def update_schedule(task_id, task):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('''
                UPDATE schedules SET
                    content=?,
                    message_type=?,
                    file_path=?,
                    buttons=?,
                    interval=?,
                    start_time=?,
                    end_time=?
                WHERE id=?
            ''', (
                task.get('content'),
                task.get('message_type'),
                task.get('file_path'),
                task.get('buttons'),
                task.get('interval'),
                task.get('start_time'),
                task.get('end_time'),
                task_id
            ))

def delete_schedule(task_id):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('DELETE FROM schedules WHERE id=?', (task_id,))

def list_schedules(chat_id):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.execute('SELECT * FROM schedules WHERE chat_id = ?', (chat_id,))
        keys = ['id', 'chat_id', 'content', 'message_type', 'file_path', 'buttons', 'interval', 'start_time', 'end_time']
        return [dict(zip(keys, row)) for row in cursor.fetchall()]