import aiosqlite
import asyncpg
from config import POSTGRES_DSN

DB_PATH = "schedules.db"
USE_PG = bool(POSTGRES_DSN)
PG_POOL = None  # 全局 Postgres 连接池

# ------------------------
# 连接池管理与初始化
# ------------------------

async def _sqlite_conn():
    return await aiosqlite.connect(DB_PATH)

async def _pg_conn():
    global PG_POOL
    if PG_POOL is None:
        PG_POOL = await asyncpg.create_pool(
            dsn=POSTGRES_DSN, min_size=1, max_size=5, statement_cache_size=0
        )
    return PG_POOL

# ========================
# 定时消息相关
# ========================

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
                cursor = await db.execute(
                    "SELECT * FROM schedules WHERE chat_id=? ORDER BY id DESC", (chat_id,))
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
                cursor = await db.execute(
                    "SELECT * FROM schedules WHERE id=?", (schedule_id,))
                row = await cursor.fetchone()
                await cursor.close()
                return dict(row) if row else None
    except Exception as e:
        print(f"[fetch_schedule] ERROR: {e}", flush=True)
        return None

async def add_schedule(chat_id, text, media_url='', media_type='', button_text='', button_url='',
                      repeat_seconds=0, time_period='', start_date='', end_date='',
                      status=1, remove_last=0, pin=0, last_message_id=None):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO schedules 
                    (chat_id, text, media_url, media_type, button_text, button_url, repeat_seconds, time_period, start_date, end_date, status, remove_last, pin, last_message_id)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                """, chat_id, text, media_url, media_type, button_text, button_url,
                     repeat_seconds, time_period, start_date, end_date,
                     status, remove_last, pin, last_message_id)
        else:
            async with _sqlite_conn() as db:
                await db.execute("""
                    INSERT INTO schedules 
                    (chat_id, text, media_url, media_type, button_text, button_url, repeat_seconds, time_period, start_date, end_date, status, remove_last, pin, last_message_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chat_id, text, media_url, media_type, button_text, button_url,
                    repeat_seconds, time_period, start_date, end_date,
                    status, remove_last, pin, last_message_id
                ))
                await db.commit()
    except Exception as e:
        print(f"[add_schedule] ERROR: {e}", flush=True)

# 兼容 create_schedule 用法
create_schedule = add_schedule

async def create_schedule_by_dict(chat_id, sch: dict):
    # 保证和 add_schedule 参数兼容
    return await add_schedule(
        chat_id,
        sch.get('text', ''),
        sch.get('media_url', ''),
        sch.get('media_type', ''),
        sch.get('button_text', ''),
        sch.get('button_url', ''),
        sch.get('repeat_seconds', 0),
        sch.get('time_period', ''),
        sch.get('start_date', ''),
        sch.get('end_date', ''),
        sch.get('status', 1),
        sch.get('remove_last', 0),
        sch.get('pin', 0),
        sch.get('last_message_id')
    )

async def update_schedule(schedule_id, sch):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE schedules SET 
                    text=$1, media_url=$2, media_type=$3, button_text=$4, button_url=$5, repeat_seconds=$6, time_period=$7, start_date=$8, end_date=$9, status=$10, remove_last=$11, pin=$12, last_message_id=$13
                    WHERE id=$14
                """,
                sch.get('text', ''), sch.get('media_url', ''), sch.get('media_type', ''),
                sch.get('button_text', ''), sch.get('button_url', ''),
                sch.get('repeat_seconds', 0), sch.get('time_period', ''),
                sch.get('start_date', ''), sch.get('end_date', ''),
                sch.get('status', 1), sch.get('remove_last', 0), sch.get('pin', 0), sch.get('last_message_id'),
                schedule_id)
        else:
            async with _sqlite_conn() as db:
                await db.execute("""UPDATE schedules SET 
                    text=?, media_url=?, media_type=?, button_text=?, button_url=?, repeat_seconds=?, time_period=?, start_date=?, end_date=?, status=?, remove_last=?, pin=?, last_message_id=?
                    WHERE id=?""",
                    (
                        sch.get('text', ''), sch.get('media_url', ''), sch.get('media_type', ''),
                        sch.get('button_text', ''), sch.get('button_url', ''),
                        sch.get('repeat_seconds', 0), sch.get('time_period', ''),
                        sch.get('start_date', ''), sch.get('end_date', ''),
                        sch.get('status', 1), sch.get('remove_last', 0), sch.get('pin', 0), sch.get('last_message_id'),
                        schedule_id
                    )
                )
                await db.commit()
    except Exception as e:
        print(f"[update_schedule] ERROR: {e}", flush=True)

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

# ========================
# 关键词回复相关
# ========================

async def init_keywords_table():
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    keyword TEXT,
                    reply TEXT,
                    fuzzy INTEGER DEFAULT 0,
                    enable INTEGER DEFAULT 1,
                    delay INTEGER DEFAULT 0
                )
                """)
        else:
            async with _sqlite_conn() as db:
                await db.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    keyword TEXT,
                    reply TEXT,
                    fuzzy INTEGER DEFAULT 0,
                    enable INTEGER DEFAULT 1,
                    delay INTEGER DEFAULT 0
                )
                """)
                await db.commit()
    except Exception as e:
        print(f"[init_keywords_table] ERROR: {e}", flush=True)

async def fetch_keywords(chat_id):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM keywords WHERE chat_id=$1 ORDER BY id DESC", chat_id)
            return [dict(row) for row in rows]
        else:
            async with _sqlite_conn() as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM keywords WHERE chat_id=? ORDER BY id DESC", (chat_id,))
                rows = await cursor.fetchall()
                await cursor.close()
                return [dict(row) for row in rows]
    except Exception as e:
        print(f"[fetch_keywords] ERROR: {e}", flush=True)
        return []

async def add_keyword(chat_id, keyword, reply, fuzzy=0, enable=1, delay=0):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO keywords (chat_id, keyword, reply, fuzzy, enable, delay) VALUES ($1, $2, $3, $4, $5, $6)",
                    chat_id, keyword, reply, fuzzy, enable, delay
                )
        else:
            async with _sqlite_conn() as db:
                await db.execute(
                    "INSERT INTO keywords (chat_id, keyword, reply, fuzzy, enable, delay) VALUES (?, ?, ?, ?, ?, ?)",
                    (chat_id, keyword, reply, fuzzy, enable, delay)
                )
                await db.commit()
    except Exception as e:
        print(f"[add_keyword] ERROR: {e}", flush=True)

async def delete_keyword(keyword_id):
    try:
        if USE_PG:
            pool = await _pg_conn()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM keywords WHERE id=$1", keyword_id)
        else:
            async with _sqlite_conn() as db:
                await db.execute("DELETE FROM keywords WHERE id=?", (keyword_id,))
                await db.commit()
    except Exception as e:
        print(f"[delete_keyword] ERROR: {e}", flush=True)

async def update_keyword(keyword_id, **kwargs):
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
                    f"UPDATE keywords SET {set_clause} WHERE id=${len(vals)+1}",
                    *vals, keyword_id
                )
        else:
            set_clause = ", ".join(f"{k}=?" for k in keys)
            vals.append(keyword_id)
            sql = f"UPDATE keywords SET {set_clause} WHERE id=?"
            async with _sqlite_conn() as db:
                await db.execute(sql, vals)
                await db.commit()
    except Exception as e:
        print(f"[update_keyword] ERROR: {e}", flush=True)

# ========================
# 关键词业务层常用接口（业务方便调用）
# ========================

async def remove_keyword(group_id, keyword):
    kws = await fetch_keywords(group_id)
    for k in kws:
        if k['keyword'] == keyword:
            await delete_keyword(k['id'])
            return True
    return False

async def update_keyword_enable(group_id, keyword, enable):
    kws = await fetch_keywords(group_id)
    for k in kws:
        if k['keyword'] == keyword:
            await update_keyword(k['id'], enable=enable)
            return True
    return False

async def update_keyword_delay(group_id, keyword, delay):
    kws = await fetch_keywords(group_id)
    for k in kws:
        if k['keyword'] == keyword:
            await update_keyword(k['id'], delay=delay)
            return True
    return False

async def update_keyword_reply(group_id, keyword, reply):
    kws = await fetch_keywords(group_id)
    for k in kws:
        if k['keyword'] == keyword:
            await update_keyword(k['id'], reply=reply)
            return True
    return False

# ========================
# 数据库初始化
# ========================

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
        # 关键词表初始化
        await init_keywords_table()
    except Exception as e:
        print(f"[init_db] ERROR: {e}", flush=True)
