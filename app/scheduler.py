from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from aiogram.types import InputMediaPhoto, InputMediaVideo, InlineKeyboardMarkup, InlineKeyboardButton
from app.bot import bot

scheduler = AsyncIOScheduler()

async def send_scheduled_message(chat_id, text, file_id=None, file_type=None, button_text=None, button_url=None):
    keyboard = None
    if button_text and button_url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=button_url)]
        ])
    if file_id and file_type:
        if file_type == "photo":
            await bot.send_photo(chat_id, photo=file_id, caption=text, reply_markup=keyboard)
        elif file_type == "video":
            await bot.send_video(chat_id, video=file_id, caption=text, reply_markup=keyboard)
        else:
            await bot.send_message(chat_id, text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)

def schedule_message(job_id, chat_id, text, run_date, file_id=None, file_type=None,
                     button_text=None, button_url=None, interval_seconds=None, start_time=None, stop_time=None):
    if interval_seconds:
        # 周期任务
        trigger = IntervalTrigger(seconds=interval_seconds, start_date=start_time, end_date=stop_time)
    else:
        # 单次任务
        trigger = DateTrigger(run_date=run_date)

    scheduler.add_job(send_scheduled_message, trigger,
                      kwargs={
                          "chat_id": chat_id,
                          "text": text,
                          "file_id": file_id,
                          "file_type": file_type,
                          "button_text": button_text,
                          "button_url": button_url
                      },
                      id=job_id, replace_existing=True)

def remove_job(job_id):
    scheduler.remove_job(job_id)