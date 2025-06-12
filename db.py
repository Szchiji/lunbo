import asyncpg
from config import NEON_DB_DSN

async def get_pool():
    return await asyncpg.create_pool(dsn=NEON_DB_DSN, min_size=1, max_size=5)

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS schedule_msgs (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            status BOOLEAN DEFAULT TRUE,
            repeat_seconds INTEGER DEFAULT 3600,
            remove_last BOOLEAN DEFAULT FALSE,
            pin BOOLEAN DEFAULT FALSE,
            media_url TEXT,
            button_text TEXT,
            button_url TEXT,
            text TEXT NOT NULL,
            start_date DATE,
            end_date DATE,
            time_period TEXT,
            last_sent_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
    await pool.close()

async def create_schedule(chat_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
        INSERT INTO schedule_msgs (chat_id, text) VALUES ($1, $2) RETURNING id
        """, chat_id, "请编辑文本内容")
    await pool.close()
    return row["id"]

async def fetch_schedules(chat_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM schedule_msgs WHERE chat_id=$1 ORDER BY id DESC", chat_id)
    await pool.close()
    return [dict(row) for row in rows]

async def fetch_all_active_schedules():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM schedule_msgs WHERE status=TRUE")
    await pool.close()
    return [dict(row) for row in rows]

async def fetch_schedule(schedule_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM schedule_msgs WHERE id=$1", schedule_id)
    await pool.close()
    return dict(row) if row else None

async def update_schedule(schedule_id, field, value):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"UPDATE schedule_msgs SET {field}=$1 WHERE id=$2", value, schedule_id)
    await pool.close()

async def update_schedule_multi(schedule_id, fields: dict):
    pool = await get_pool()
    set_clause = ", ".join([f"{k}=${i+1}" for i, k in enumerate(fields.keys())])
    values = list(fields.values())
    values.append(schedule_id)
    async with pool.acquire() as conn:
        await conn.execute(f"UPDATE schedule_msgs SET {set_clause} WHERE id=${len(values)}", *values)
    await pool.close()

async def delete_schedule(schedule_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM schedule_msgs WHERE id=$1", schedule_id)
    await pool.close()
