import os
import aiosqlite
import asyncpg
from config import POSTGRES_DSN

DB_PATH = "schedules.db"

# -------- 数据库引擎自动切换 --------
USE_PG = bool(POSTGRES_DSN)

# -------- SQLite实现 --------
async def _sqlite_conn():
    return await aiosqlite.connect(DB_PATH)

# -------- PostgreSQL实现 --------
async def _pg_conn():
    return await asyncpg.create_pool(dsn=POSTGRES_DSN, min_size=1, max_size=5)

# -------- 获取全部定时消息 --------
async def fetch_schedules(chat_id):
    if USE_PG:
        pool = await _pg_conn()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM schedules WHERE chat_id=$1 ORDER BY id DESC", chat_id)
        await pool.close()
        return [dict(row) for row in rows]
    else:
        async with _sqlite_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM schedules WHERE chat_id=? ORDER BY id DESC", (chat_id,))
            rows = await cursor.fetchall()
            await cursor.close()
            return [dict(row) for row in rows]

# -------- 获取单条定时消息 --------
async def fetch_schedule(schedule_id):
    if USE_PG:
        pool = await _pg_conn()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM schedules WHERE id=$1", schedule_id)
        await pool.close()
        return dict(row) if row else None
    else:
        async with _sqlite_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM schedules WHERE id=?", (schedule_id,))
            row = await cursor.fetchone()
            await cursor.close()
            return dict(row) if row else None

# -------- 创建定时消息 --------
async def create_schedule(chat_id, sch):
    if USE_PG:
        pool = await _pg_conn()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO schedules 
                (chat_id, text, media_url, button_text, button_url, repeat_seconds, time_period, start_date, end_date, status, remove_last, pin)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            """, chat_id, sch.get('text', ''), sch.get('media_url', ''),
                sch.get('button_text', ''), sch.get('button_url', ''),
                sch.get('repeat_seconds', 0), sch.get('time_period', ''),
                sch.get('start_date', ''), sch.get('end_date', ''),
                sch.get('status', 1), sch.get('remove_last', 0), sch.get('pin', 0)
            )
        await pool.close()
    else:
        async with _sqlite_conn() as db:
            await db.execute("""INSERT INTO schedules 
                (chat_id, text, media_url, button_text, button_url, repeat_seconds, time_period, start_date, end_date, status, remove_last, pin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    chat_id, sch.get('text', ''), sch.get('media_url', ''),
                    sch.get('button_text', ''), sch.get('button_url', ''),
                    sch.get('repeat_seconds', 0), sch.get('time_period', ''),
                    sch.get('start_date', ''), sch.get('end_date', ''),
                    sch.get('status', 1), sch.get('remove_last', 0), sch.get('pin', 0)
                )
            )
            await db.commit()

# -------- 更新定时消息 --------
async def update_schedule(schedule_id, sch):
    if USE_PG:
        pool = await _pg_conn()
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE schedules SET 
                text=$1, media_url=$2, button_text=$3, button_url=$4, repeat_seconds=$5, time_period=$6, start_date=$7, end_date=$8, status=$9, remove_last=$10, pin=$11
                WHERE id=$12
            """,
            sch.get('text', ''), sch.get('media_url', ''),
            sch.get('button_text', ''), sch.get('button_url', ''),
            sch.get('repeat_seconds', 0), sch.get('time_period', ''),
            sch.get('start_date', ''), sch.get('end_date', ''),
            sch.get('status', 1), sch.get('remove_last', 0), sch.get('pin', 0),
            schedule_id)
        await pool.close()
    else:
        async with _sqlite_conn() as db:
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

# -------- 批量更新 --------
async def update_schedule_multi(schedule_id, **kwargs):
    if not kwargs:
        return
    keys = list(kwargs.keys())
    vals = list(kwargs.values())
    if USE_PG:
        set_clause = ", ".join(f"{k}=${i+1}" for i, k in enumerate(keys))
        pool = await _pg_conn()
        async with pool.acquire() as conn:
            await conn.execute(
                f"UPDATE schedules SET {set_clause} WHERE id=${len(vals)+1}",
                *vals, schedule_id
            )
        await pool.close()
    else:
        set_clause = ", ".join(f"{k}=?" for k in keys)
        vals.append(schedule_id)
        sql = f"UPDATE schedules SET {set_clause} WHERE id=?"
        async with _sqlite_conn() as db:
            await db.execute(sql, vals)
            await db.commit()

# -------- 删除定时消息 --------
async def delete_schedule(schedule_id):
    if USE_PG:
        pool = await _pg_conn()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM schedules WHERE id=$1", schedule_id)
        await pool.close()
    else:
        async with _sqlite_conn() as db:
            await db.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
            await db.commit()

# -------- 初始化表结构 --------
async def init_db():
    if USE_PG:
        pool = await _pg_conn()
        async with pool.acquire() as conn:
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
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
        await pool.close()
    else:
        async with _sqlite_conn() as db:
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
