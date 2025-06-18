import aiosqlite
import asyncpg
from config import POSTGRES_DSN

DB_PATH = "schedules.db"
USE_PG = bool(POSTGRES_DSN)
PG_POOL = None

async def _sqlite_conn():
    return await aiosqlite.connect(DB_PATH)

async def _pg_conn():
    global PG_POOL
    if PG_POOL is None:
        PG_POOL = await asyncpg.create_pool(
            dsn=POSTGRES_DSN, min_size=1, max_size=5, statement_cache_size=0
        )
    return PG_POOL

async def fetch_schedules(chat_id):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM schedules WHERE chat_id=$1 ORDER BY id DESC", chat_id)
            return [dict(row) for row in rows]
        else:
            async with _sqlite_conn() as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM schedules WHERE chat_id=? ORDER BY id DESC", (chat_id,))
                rows = await cursor.fetchall()
                await cursor.close()
                return [dict(row) for row in rows]
    except Exception as e:
        print(f"[fetch_schedules] ERROR: {e}", flush=True)
        return []

async def fetch_schedule(schedule_id):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM schedules WHERE id=$1", schedule_id)
            return dict(row) if row else None
        else:
            async with _sqlite_conn() as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,))
                row = await cursor.fetchone()
                await cursor.close()
                return dict(row) if row else None
    except Exception as e:
        print(f"[fetch_schedule] ERROR: {e}", flush=True)
        return None

async def create_schedule(chat_id, sch):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO schedules 
                    (chat_id, text, media_url, media_type, button_text, button_url, repeat_seconds, time_period, start_date, end_date, status, remove_last, pin, last_message_id)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                """, chat_id, sch.get('text', ''), sch.get('media_url', ''), sch.get('media_type', ''),
                    sch.get('button_text', ''), sch.get('button_url', ''),
                    sch.get('repeat_seconds', 0), sch.get('time_period', ''),
                    sch.get('start_date', ''), sch.get('end_date', ''),
                    sch.get('status', 1), sch.get('remove_last', 0), sch.get('pin', 0), sch.get('last_message_id')
                )
        else:
            async with _sqlite_conn() as db:
                await db.execute("""INSERT INTO schedules 
                    (chat_id, text, media_url, media_type, button_text, button_url, repeat_seconds, time_period, start_date, end_date, status, remove_last, pin, last_message_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        chat_id, sch.get('text', ''), sch.get('media_url', ''), sch.get('media_type', ''),
                        sch.get('button_text', ''), sch.get('button_url', ''),
                        sch.get('repeat_seconds', 0), sch.get('time_period', ''),
                        sch.get('start_date', ''), sch.get('end_date', ''),
                        sch.get('status', 1), sch.get('remove_last', 0), sch.get('pin', 0), sch.get('last_message_id')
                    )
                )
                await db.commit()
    except Exception as e:
        print(f"[create_schedule] ERROR: {e}", flush=True)

async def update_schedule_multi(schedule_id, **kwargs):
    if not kwargs:
        return
    keys = list(kwargs.keys())
    vals = list(kwargs.values())
    try:
        if USE_PG:
            set_clause = ", ".join(f"{k}=${i+1}" for i, k in enumerate(keys))
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute(
                    f"UPDATE schedules SET {set_clause} WHERE id=${len(vals)+1}",
                    *vals, schedule_id
                )
        else:
            set_clause = ", ".join(f"{k}=?" for k in keys)
            vals.append(schedule_id)
            sql = f"UPDATE schedules SET {set_clause} WHERE id=?"
            async with _sqlite_conn() as db:
                await db.execute(sql, vals)
                await db.commit()
    except Exception as e:
        print(f"[update_schedule_multi] ERROR: {e}", flush=True)

async def update_schedule_last_message_id(schedule_id, message_id):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute("UPDATE schedules SET last_message_id=$1 WHERE id=$2", message_id, schedule_id)
        else:
            async with _sqlite_conn() as db:
                await db.execute("UPDATE schedules SET last_message_id=? WHERE id=?", (message_id, schedule_id))
                await db.commit()
    except Exception as e:
        print(f"[update_schedule_last_message_id] ERROR: {e}", flush=True)

async def delete_schedule(schedule_id):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM schedules WHERE id=$1", schedule_id)
        else:
            async with _sqlite_conn() as db:
                await db.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
                await db.commit()
    except Exception as e:
        print(f"[delete_schedule] ERROR: {e}", flush=True)

async def init_db():
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    text TEXT,
                    media_url TEXT,
                    media_type TEXT,
                    button_text TEXT,
                    button_url TEXT,
                    repeat_seconds INTEGER,
                    time_period TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    status INTEGER DEFAULT 1,
                    remove_last INTEGER DEFAULT 0,
                    pin INTEGER DEFAULT 0,
                    last_message_id BIGINT
                )
                """)
        else:
            async with _sqlite_conn() as db:
                await db.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    text TEXT,
                    media_url TEXT,
                    media_type TEXT,
                    button_text TEXT,
                    button_url TEXT,
                    repeat_seconds INTEGER,
                    time_period TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    status INTEGER DEFAULT 1,
                    remove_last INTEGER DEFAULT 0,
                    pin INTEGER DEFAULT 0,
                    last_message_id INTEGER
                )
                """)
                await db.commit()
    except Exception as e:
        print(f"[init_db] ERROR: {e}", flush=True)
