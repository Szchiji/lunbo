from db import fetch_schedules
from modules.send_media import send_media
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

def is_schedule_active(sch):
    if not sch.get("status", 1):
        return False
    now = datetime.utcnow()
    fmt = "%Y-%m-%d %H:%M"
    # 检查起止日期
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
    # 检查时间段（如 09:00-18:00）
    period = sch.get("time_period")
    if period:
        try:
            s, e = period.split("-")
            now_t = now.time()
            s_t = datetime.strptime(s, "%H:%M").time()
            e_t = datetime.strptime(e, "%H:%M").time()
            if not (s_t <= now_t <= e_t):
                return False
        except Exception:
            pass
    return True

async def broadcast_task(context):
    if "last_sent" not in context.bot_data:
        context.bot_data["last_sent"] = {}
    if "last_time" not in context.bot_data:
        context.bot_data["last_time"] = {}
    last_sent = context.bot_data["last_sent"]
    last_time = context.bot_data["last_time"]
    for chat_id in context.bot_data.get("group_ids", []):
        schedules = await fetch_schedules(chat_id)
        for sch in schedules:
            if not is_schedule_active(sch):
                continue
            key = (chat_id, sch["id"])
            # 检查重复周期
            repeat = sch.get("repeat_seconds", 0)
            now = datetime.utcnow()
            prev_time = last_time.get(key)
            if repeat and prev_time and (now - prev_time).total_seconds() < repeat:
                continue  # 未到下次推送时间
            # 删除上一条
            if sch.get("remove_last"):
                last_msg_id = last_sent.get(key)
                if last_msg_id:
                    try:
                        await context.bot.delete_message(chat_id, last_msg_id)
                    except Exception as e:
                        print(f"[自动删除消息失败] chat_id={chat_id}, schedule_id={sch['id']}: {e}")
            # 构建按钮
            reply_markup = None
            if sch.get("button_text") and sch.get("button_url"):
                reply_markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(sch["button_text"], url=sch["button_url"])]])
            # 发送新消息（推荐用 send_media 工具）
            try:
                msg = None
                media_url = sch.get("media_url")
                media_type = sch.get("media_type")
                text = sch.get("text", "")
                if media_url:
                    msg = await send_media(context.bot, chat_id, media_url, caption=text, buttons=reply_markup, media_type=media_type)
                    if not msg:  # fallback
                        msg = await context.bot.send_message(chat_id, text + f"\n[媒体] {media_url}", reply_markup=reply_markup)
                else:
                    msg = await context.bot.send_message(chat_id, text, reply_markup=reply_markup)
                if msg:
                    last_sent[key] = msg.message_id
                    last_time[key] = now
            except Exception as e:
                print(f"[推送到群{chat_id}出错]：{e}")

def schedule_broadcast_jobs(application, group_ids):
    application.bot_data["group_ids"] = group_ids
    application.job_queue.run_repeating(
        broadcast_task,
        interval=60,
        first=10
    )
