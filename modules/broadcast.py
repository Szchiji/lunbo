from db import fetch_schedules
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

def is_schedule_active(sch):
    # status=1才推送
    if not sch.get("status"):
        return False
    now = datetime.utcnow()
    fmt = "%Y-%m-%d %H:%M"
    # 起始时间
    if sch.get("start_date"):
        try:
            start = datetime.strptime(sch["start_date"], fmt)
            if now < start:
                return False
        except Exception:
            pass
    # 结束时间
    if sch.get("end_date"):
        try:
            end = datetime.strptime(sch["end_date"], fmt)
            if now > end:
                return False
        except Exception:
            pass
    return True

async def broadcast_task(context):
    for chat_id in context.bot_data.get("group_ids", []):
        schedules = await fetch_schedules(chat_id)
        for sch in schedules:
            if is_schedule_active(sch):
                # 支持媒体、按钮
                if sch.get("media_url"):
                    if sch["media_url"].endswith((".jpg", ".png")) or sch["media_url"].startswith("AgAC"):
                        await context.bot.send_photo(chat_id, sch["media_url"], caption=sch["text"])
                    elif sch["media_url"].endswith((".mp4",)) or sch["media_url"].startswith("BAAC"):
                        await context.bot.send_video(chat_id, sch["media_url"], caption=sch["text"])
                    else:
                        await context.bot.send_message(chat_id, sch["text"] + f"\n[媒体] {sch['media_url']}")
                else:
                    if sch.get("button_text") and sch.get("button_url"):
                        reply_markup = InlineKeyboardMarkup(
                            [[InlineKeyboardButton(sch["button_text"], url=sch["button_url"])]])
                        await context.bot.send_message(chat_id, sch["text"], reply_markup=reply_markup)
                    else:
                        await context.bot.send_message(chat_id, sch["text"])

def schedule_broadcast_jobs(application, group_ids):
    application.bot_data["group_ids"] = group_ids
    application.job_queue.run_repeating(
        broadcast_task,
        interval=60,   # 每60秒执行一次
        first=10       # 启动后10秒首次执行
    )
