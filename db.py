import asyncpg
from config import POSTGRES_DSN

async def get_conn():
    return await asyncpg.connect(POSTGRES_DSN)

async def init_db():
    conn = await get_conn()
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
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
    ''')
    await conn.close()

async def fetch_schedules(chat_id):
    conn = await get_conn()
    rows = await conn.fetch("SELECT * FROM schedules WHERE chat_id=$1 ORDER BY id DESC", chat_id)
    await conn.close()
    return [dict(row) for row in rows]

async def fetch_schedule(schedule_id):
    conn = await get_conn()
    row = await conn.fetchrow("SELECT * FROM schedules WHERE id=$1", schedule_id)
    await conn.close()
    return dict(row) if row else None

async def create_schedule(chat_id, sch):
    conn = await get_conn()
    await conn.execute('''
        INSERT INTO schedules (chat_id, text, media_url, button_text, button_url, repeat_seconds, time_period, start_date, end_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ''',
        chat_id,
        sch.get('text', ''),
        sch.get('media_url', ''),
        sch.get('button_text', ''),
        sch.get('button_url', ''),
        sch.get('repeat_seconds', 0),
        sch.get('time_period', ''),
        sch.get('start_date', ''),
        sch.get('end_date', ''),
    )
    await conn.close()

async def update_schedule(schedule_id, key, value):
    conn = await get_conn()
    await conn.execute(f'UPDATE schedules SET {key}=$1 WHERE id=$2', value, schedule_id)
    await conn.close()

async def update_schedule_multi(schedule_id, values: dict):
    keys = ', '.join([f"{k}=${i+1}" for i, k in enumerate(values.keys())])
    params = list(values.values()) + [schedule_id]
    set_clause = ', '.join([f"{k}=${i+1}" for i, k in enumerate(values.keys())])
    conn = await get_conn()
    await conn.execute(f"UPDATE schedules SET {set_clause} WHERE id=${len(params)}", *params)
    await conn.close()

async def delete_schedule(schedule_id):
    conn = await get_conn()
    await conn.execute("DELETE FROM schedules WHERE id=$1", schedule_id)
    await conn.close()
