import logging
from db import fetch_schedules
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

async def broadcast_task(context):
    for chat_id in context.bot_data.get("group_ids", []):
        schedules = await fetch_schedules(chat_id)
        # 示例：只发启用的第一个定时消息
        for sch in schedules:
            if sch["status"]:
                kwargs = {}
                if sch.get("media_type") == "photo" and sch.get("media_file_id"):
                    kwargs["photo"] = sch["media_file_id"]
                elif sch.get("media_type") == "video" and sch.get("media_file_id"):
                    kwargs["video"] = sch["media_file_id"]
                if sch.get("button_text") and sch.get("button_url"):
                    reply_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton(sch["button_text"], url=sch["button_url"])]
                    ])
                    kwargs["reply_markup"] = reply_markup
                await context.bot.send_message(chat_id, sch["text"], **kwargs)
                break

def schedule_broadcast_jobs(application, group_ids):
    application.bot_data["group_ids"] = group_ids
    application.job_queue.run_repeating(
        broadcast_task,
        interval=60,
        first=10
    )
