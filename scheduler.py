from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from bot_init import bot

scheduler = AsyncIOScheduler()
scheduler.start()

def schedule_message(chat_id: int, data: dict):
    start_time = data['start_time']
    end_time = data['end_time']
    interval = data['interval']
    scheduler.add_job(
        send_message,
        trigger=IntervalTrigger(minutes=interval, start_date=start_time, end_date=end_time),
        args=[chat_id, data],
        id=f"{chat_id}-{start_time.timestamp()}"
    )

async def send_message(chat_id: int, data: dict):
    text = data['text']
    button = data.get('button')
    media = data['media']
    if button:
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text=button, url="https://example.com"))
    else:
        markup = None
    if media.photo:
        await bot.send_photo(chat_id, media.photo[-1].file_id, caption=text, reply_markup=markup)
    elif media.video:
        await bot.send_video(chat_id, media.video.file_id, caption=text, reply_markup=markup)