from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import sqlite3
from aiogram import Bot
from app.config import DATABASE_PATH

scheduler = AsyncIOScheduler()

def load_scheduled_messages(bot: Bot):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages")
    for row in cursor.fetchall():
        user_id, media_type, file_id, text, buttons, interval, start_time, end_time = row[1:]
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)

        scheduler.add_job(
            send_scheduled_message,
            'interval',
            seconds=interval,
            start_date=start_dt,
            end_date=end_dt,
            args=(bot, user_id, media_type, file_id, text, buttons)
        )
    conn.close()

async def send_scheduled_message(bot: Bot, user_id, media_type, file_id, text, buttons):
    if media_type == 'photo':
        await bot.send_photo(user_id, photo=file_id, caption=text)
    elif media_type == 'video':
        await bot.send_video(user_id, video=file_id, caption=text)