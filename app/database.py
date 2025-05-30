import sqlite3
import os
from app.config import DATABASE_PATH

def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            media_type TEXT,
            media_file_id TEXT,
            text TEXT,
            buttons TEXT,
            interval INTEGER,
            start_time TEXT,
            end_time TEXT
        )
    """)
    conn.commit()
    conn.close()