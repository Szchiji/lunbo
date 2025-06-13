import aiosqlite

DB_PATH = "schedules.db"

async def fetch_schedules(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM schedules WHERE chat_id=? ORDER BY id DESC", (chat_id,))
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]

async def fetch_schedule(schedule_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM schedules WHERE id=?", (schedule_id,))
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None

async def create_schedule(chat_id, sch):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO schedules 
            (chat_id, text, media_url, button_text, button_url, repeat_seconds, time_period, start_date, end_date, status, remove_last, pin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                chat_id, sch.get('text', ''), sch.get('media_url', ''),
                sch.get('button_text', ''), sch.get('button_url', ''),
                sch.get('repeat_seconds', 0), sch.get('time_period', ''),
                sch.get('start_date', ''), sch.get('end_date', ''),
                1,  # status: 启用
                0,  # remove_last
                0   # pin
            )
        )
        await db.commit()

async def update_schedule(schedule_id, sch):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""UPDATE schedules SET 
            text=?, media_url=?, button_text=?, button_url=?, repeat_seconds=?, time_period=?, start_date=?, end_date=?, status=?, remove_last=?, pin=?
            WHERE id=?""",
            (
                sch.get('text', ''), sch.get('media_url', ''),
                sch.get('button_text', ''), sch.get('button_url', ''),
                sch.get('repeat_seconds', 0), sch.get('time_period', ''),
                sch.get('start_date', ''), sch.get('end_date', ''),
                sch.get('status', 1), sch.get('remove_last', 0), sch.get('pin', 0),
                schedule_id
            )
        )
        await db.commit()

async def update_schedule_multi(schedule_id, **kwargs):
    keys = []
    vals = []
    for k, v in kwargs.items():
        keys.append(f"{k}=?")
        vals.append(v)
    vals.append(schedule_id)
    sql = f"UPDATE schedules SET {', '.join(keys)} WHERE id=?"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(sql, vals)
        await db.commit()

async def delete_schedule(schedule_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
        await db.commit()


# 初始化表结构
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT,
            media_url TEXT,
            button_text TEXT,
            button_url TEXT,
            repeat_seconds INTEGER,
            time_period TEXT,
            start_date TEXT,
            end_date TEXT,
            status INTEGER DEFAULT 1,
            remove_last INTEGER DEFAULT 0,
            pin INTEGER DEFAULT 0
        )
        """)
        await db.commit()
