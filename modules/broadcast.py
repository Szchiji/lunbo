from db import fetch_schedules
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

def is_schedule_active(sch):
    if not sch.get("status", 1):
        return False
    now = datetime.utcnow()
    fmt = "%Y-%m-%d %H:%M"
    if sch.get("start_date"):
        try:
            start = datetime.strptime(sch["start_date"], fmt)
            if now < start:
                return False
        except Exception:
            pass
    if sch.get("end_date"):
        try:
            end = datetime.strptime(sch["end_date"], fmt)
            if now > end:
                return False
        except Exception:
            pass
    return True

async def broadcast_task(context):
    if "last_sent" not in context.bot_data:
        context.bot_data["last_sent"] = {}  # {(chat_id, schedule_id): message_id}
    last_sent = context.bot_data["last_sent"]

    for chat_id in context.bot_data.get("group_ids", []):
        schedules = await fetch_schedules(chat_id)
        for sch in schedules:
            if is_schedule_active(sch):
                key = (chat_id, sch["id"])
                # 删除上一条
                if sch.get("remove_last"):
                    last_msg_id = last_sent.get(key)
                    if last_msg_id:
                        try:
                            await context.bot.delete_message(chat_id, last_msg_id)
                        except Exception as e:
                            print(f"[自动删除消息失败] chat_id={chat_id}, schedule_id={sch['id']}: {e}")
                # 发送新消息
                try:
                    msg = None
                    if sch.get("media_url"):
                        if sch["media_url"].endswith((".jpg", ".png")) or sch["media_url"].startswith("AgAC"):
                            msg = await context.bot.send_photo(chat_id, sch["media_url"], caption=sch["text"])
                        elif sch["media_url"].endswith((".mp4",)) or sch["media_url"].startswith("BAAC"):
                            msg = await context.bot.send_video(chat_id, sch["media_url"], caption=sch["text"])
                        else:
                            msg = await context.bot.send_message(chat_id, sch["text"] + f"\n[媒体] {sch['media_url']}")
                    else:
                        if sch.get("button_text") and sch.get("button_url"):
                            reply_markup = InlineKeyboardMarkup(
                                [[InlineKeyboardButton(sch["button_text"], url=sch["button_url"])]])
                            msg = await context.bot.send_message(chat_id, sch["text"], reply_markup=reply_markup)
                        else:
                            msg = await context.bot.send_message(chat_id, sch["text"])
                    # 记录最新消息id
                    if msg:
                        last_sent[key] = msg.message_id
                except Exception as e:
                    print(f"[推送到群{chat_id}出错]：{e}")

def schedule_broadcast_jobs(application, group_ids):
    application.bot_data["group_ids"] = group_ids
    application.job_queue.run_repeating(
        broadcast_task,
        interval=60,
        first=10
    )
