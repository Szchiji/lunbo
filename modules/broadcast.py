import asyncio
import logging
from datetime import datetime, time, timedelta

from db import fetch_all_active_schedules, update_schedule
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def _is_now_within_period(now: datetime, period_str: str):
    if not period_str:
        return True
    try:
        start, end = period_str.split('-')
        t1 = time.fromisoformat(start)
        t2 = time.fromisoformat(end)
        now_t = now.time()
        if t1 <= t2:
            return t1 <= now_t <= t2
        else:
            return now_t >= t1 or now_t <= t2
    except Exception:
        return True

def _is_now_within_dates(now: datetime, start_date, end_date):
    if start_date and now.date() < start_date:
        return False
    if end_date and now.date() > end_date:
        return False
    return True

async def send_schedule_message(bot, chat_id, schedule):
    reply_markup = None
    if schedule["button_text"] and schedule["button_url"]:
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(schedule["button_text"], url=schedule["button_url"])]
        ])
    try:
        if schedule["media_url"]:
            if schedule["media_url"].endswith(('.jpg', '.jpeg', '.png', '.gif')):
                msg = await bot.send_photo(chat_id, schedule["media_url"], caption=schedule["text"], reply_markup=reply_markup)
            elif schedule["media_url"].endswith(('.mp4', '.mov', '.mkv')):
                msg = await bot.send_video(chat_id, schedule["media_url"], caption=schedule["text"], reply_markup=reply_markup)
            else:
                msg = await bot.send_photo(chat_id, schedule["media_url"], caption=schedule["text"], reply_markup=reply_markup)
        else:
            msg = await bot.send_message(chat_id, schedule["text"], reply_markup=reply_markup)
        if schedule["pin"]:
            await bot.pin_chat_message(chat_id, msg.message_id, disable_notification=True)
        if schedule["remove_last"]:
            # 可扩展：记录并删除上一条消息
            pass
        await update_schedule(schedule["id"], "last_sent_time", datetime.now())
    except Exception as e:
        logging.warning(f"发送定时消息失败: {e}")

async def broadcast_task(bot, group_ids):
    now = datetime.now()
    schedules = await fetch_all_active_schedules()
    for schedule in schedules:
        if schedule["chat_id"] not in group_ids:
            continue
        if not schedule["status"]:
            continue
        if not _is_now_within_dates(now, schedule["start_date"], schedule["end_date"]):
            continue
        if not _is_now_within_period(now, schedule["time_period"]):
            continue
        last_sent_time = schedule.get("last_sent_time")
        interval = timedelta(seconds=schedule["repeat_seconds"])
        if last_sent_time and now - last_sent_time < interval:
            continue  # 本周期已发
        await send_schedule_message(bot, schedule["chat_id"], schedule)

def schedule_broadcast_jobs(application, group_ids):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(broadcast_task(application.bot, group_ids)), 'interval', seconds=60)
    scheduler.start()
    logging.info("定时轮播任务已启动")
    return scheduler
