from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import types
from .bot import bot

scheduler = AsyncIOScheduler()
scheduler.start()

async def send_scheduled_message(data):
    chat_id = data['media'].chat.id
    if data['media'].photo:
        await bot.send_photo(chat_id=chat_id, photo=data['media'].photo[-1].file_id, caption=data['text'])
    elif data['media'].video:
        await bot.send_video(chat_id=chat_id, video=data['media'].video.file_id, caption=data['text'])

def schedule_message(data):
    interval_minutes = data['interval']
    start_time = data['start_time']
    end_time = data['end_time']
    scheduler.add_job(send_scheduled_message, 'interval', minutes=interval_minutes, start_date=start_time, end_date=end_time, args=[data])