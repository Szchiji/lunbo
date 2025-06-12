import aiosqlite

DB_PATH = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            text TEXT,
            media_url TEXT,
            button_text TEXT,
            button_url TEXT,
            repeat_seconds INTEGER DEFAULT 3600,
            status INTEGER DEFAULT 0,
            remove_last INTEGER DEFAULT 0,
            pin INTEGER DEFAULT 0,
            time_period TEXT,
            start_date TEXT,
            end_date TEXT
        )''')
        await db.commit()

async def fetch_schedules(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM schedules WHERE chat_id=?", (chat_id,))
        rows = await cursor.fetchall()
        return [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

async def fetch_schedule(schedule_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,))
        row = await cursor.fetchone()
        if not row: return None
        return dict(zip([column[0] for column in cursor.description], row))

async def create_schedule(chat_id, sch=None):
    sch = sch or {}
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            '''INSERT INTO schedules (chat_id, text, media_url, button_text, button_url, repeat_seconds, status, remove_last, pin, time_period, start_date, end_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                chat_id,
                sch.get("text", ""),
                sch.get("media_url", ""),
                sch.get("button_text", ""),
                sch.get("button_url", ""),
                sch.get("repeat_seconds", 3600),
                1,
                0,
                0,
                sch.get("time_period", ""),
                sch.get("start_date", ""),
                sch.get("end_date", "")
            )
        )
        await db.commit()
        return cursor.lastrowid

async def update_schedule(schedule_id, key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE schedules SET {key}=? WHERE id=?", (value, schedule_id))
        await db.commit()

async def update_schedule_multi(schedule_id, kv: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        fields = ",".join([f"{k}=?" for k in kv.keys()])
        values = list(kv.values()) + [schedule_id]
        await db.execute(f"UPDATE schedules SET {fields} WHERE id=?", values)
        await db.commit()

async def delete_schedule(schedule_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
        await db.commit()
