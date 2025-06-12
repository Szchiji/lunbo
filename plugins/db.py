import os
import asyncpg

DB_URI = os.environ.get("DATABASE_URL")

async def get_pool():
    if not hasattr(get_pool, "pool"):
        get_pool.pool = await asyncpg.create_pool(dsn=DB_URI)
    return get_pool.pool

# 会员
async def add_member(chat_id: int, user_id: int, expire_at):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO members (chat_id, user_id, expire_at) VALUES ($1, $2, $3) "
        "ON CONFLICT (chat_id, user_id) DO UPDATE SET expire_at=$3",
        chat_id, user_id, expire_at
    )
async def remove_member(chat_id: int, user_id: int):
    pool = await get_pool()
    await pool.execute(
        "DELETE FROM members WHERE chat_id=$1 AND user_id=$2",
        chat_id, user_id
    )
async def is_member(chat_id: int, user_id: int):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT expire_at FROM members WHERE chat_id=$1 AND user_id=$2",
        chat_id, user_id
    )
    import datetime
    if not row:
        return False
    expire = row["expire_at"]
    if expire and expire < datetime.datetime.utcnow():
        return False
    return True
async def list_members(chat_id: int):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT user_id, expire_at FROM members WHERE chat_id=$1",
        chat_id
    )
    return rows

# 自动回复
async def add_auto_reply_db(chat_id, keyword, reply, mtype, media, btns):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO auto_replies (chat_id, keyword, reply, media_type, media_url, buttons) VALUES ($1,$2,$3,$4,$5,$6) "
        "ON CONFLICT (chat_id, keyword) DO UPDATE SET reply=$3, media_type=$4, media_url=$5, buttons=$6, enabled=TRUE",
        chat_id, keyword, reply, mtype, media, btns
    )
async def get_auto_replies(chat_id):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT keyword, reply, media_type, media_url, buttons, enabled FROM auto_replies WHERE chat_id=$1",
        chat_id
    )
    return rows
async def get_enabled_auto_replies(chat_id):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT keyword, reply, media_type, media_url, buttons FROM auto_replies WHERE chat_id=$1 AND enabled=TRUE",
        chat_id
    )
    return rows
async def toggle_auto_reply(chat_id, keyword):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT enabled FROM auto_replies WHERE chat_id=$1 AND keyword=$2", chat_id, keyword)
    if not row: return False
    enabled = not row["enabled"]
    await pool.execute(
        "UPDATE auto_replies SET enabled=$1 WHERE chat_id=$2 AND keyword=$3",
        enabled, chat_id, keyword
    )
    return enabled
async def delete_auto_reply(chat_id, keyword):
    pool = await get_pool()
    await pool.execute("DELETE FROM auto_replies WHERE chat_id=$1 AND keyword=$2", chat_id, keyword)

# 定时消息
async def add_schedule_db(chat_id, content, cron, mtype, media, btns):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO scheduled_msgs (chat_id, content, cron, media_type, media_url, buttons) VALUES ($1,$2,$3,$4,$5,$6)",
        chat_id, content, cron, mtype, media, btns
    )
async def get_schedules(chat_id):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, content, cron, media_type, media_url, buttons, enabled FROM scheduled_msgs WHERE chat_id=$1",
        chat_id
    )
    return rows
async def toggle_schedule(chat_id, sid):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT enabled FROM scheduled_msgs WHERE chat_id=$1 AND id=$2", chat_id, sid)
    if not row: return False
    enabled = not row["enabled"]
    await pool.execute(
        "UPDATE scheduled_msgs SET enabled=$1 WHERE chat_id=$2 AND id=$3",
        enabled, chat_id, sid
    )
    return enabled
async def delete_schedule(chat_id, sid):
    pool = await get_pool()
    await pool.execute("DELETE FROM scheduled_msgs WHERE chat_id=$1 AND id=$2", chat_id, sid)
