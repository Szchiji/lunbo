import sqlite3

DB_PATH = "data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id TEXT PRIMARY KEY,
        chat_id INTEGER,
        message_type TEXT,
        content TEXT,
        file_path TEXT,
        buttons TEXT,
        interval INTEGER,
        start_time TEXT,
        end_time TEXT,
        active INTEGER DEFAULT 1
    )
    """)
    conn.commit()
    conn.close()

def add_schedule(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    INSERT INTO schedules (id, chat_id, message_type, content, file_path, buttons, interval, start_time, end_time, active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (data['id'], data['chat_id'], data['message_type'], data['content'], data['file_path'], data['buttons'], data['interval'], data['start_time'], data['end_time']))
    conn.commit()
    conn.close()

def update_schedule(id_, data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    UPDATE schedules SET message_type=?, content=?, file_path=?, buttons=?, interval=?, start_time=?, end_time=? WHERE id=?
    """, (data['message_type'], data['content'], data['file_path'], data['buttons'], data['interval'], data['start_time'], data['end_time'], id_))
    conn.commit()
    conn.close()

def deactivate_schedule(id_):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE schedules SET active=0 WHERE id=?", (id_,))
    conn.commit()
    conn.close()

def get_active_schedules():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM schedules WHERE active=1")
    rows = c.fetchall()
    conn.close()
    keys = ['id', 'chat_id', 'message_type', 'content', 'file_path', 'buttons', 'interval', 'start_time', 'end_time', 'active']
    return [dict(zip(keys, row)) for row in rows]

def get_schedule_by_id(id_):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM schedules WHERE id=?", (id_,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = ['id', 'chat_id', 'message_type', 'content', 'file_path', 'buttons', 'interval', 'start_time', 'end_time', 'active']
    return dict(zip(keys, row))