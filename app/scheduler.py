from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InputMediaPhoto, InputMediaVideo
import asyncio
from database import get_tasks

scheduler = AsyncIOScheduler()

def schedule_tasks(bot: Bot):
    tasks = get_tasks()
    for task in tasks:
        scheduler.add_job(
            send_task_message,
            "interval",
            seconds=task[8],
            args=[bot, task],
            id=str(task[0]),
            replace_existing=True
        )

async def send_task_message(bot: Bot, task):
    chat_id = task[1]
    media_type = task[2]
    media_path = task[3]
    caption = task[4]
    buttons = task[5]

    markup = None
    if buttons:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        btns = [InlineKeyboardButton(text=b.strip(), url=b.strip()) for b in buttons.split(",")]
        markup = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in btns])

    if media_type == "photo":
        await bot.send_photo(chat_id, photo=media_path, caption=caption, reply_markup=markup)
    elif media_type == "video":
        await bot.send_video(chat_id, video=media_path, caption=caption, reply_markup=markup)
    else:
        await bot.send_message(chat_id, caption, reply_markup=markup)
