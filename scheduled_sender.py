import asyncio
from datetime import datetime, time as dtime
from db import fetch_schedules
from telegram.constants import ParseMode
from modules.sender import send_media

last_sent = {}

def _in_time_period(period: str, now: datetime):
    if not period:
        return True
    try:
        start_str, end_str = period.split('-')
        start = dtime.fromisoformat(start_str)
        end = dtime.fromisoformat(end_str)
        now_time = now.time()
        if start <= end:
            return start <= now_time <= end
        else:
            return now_time >= start or now_time <= end
    except Exception:
        return True

def _in_date_range(start_date: str, end_date: str, now: datetime):
    fmt = "%Y-%m-%d %H:%M"
    fmt_short = "%Y-%m-%d"
    def parse(dt):
        if not dt or dt in ["不限", ""]:
            return None
        try:
            return datetime.strptime(dt, fmt)
        except Exception:
            try:
                return datetime.strptime(dt, fmt_short)
            except Exception:
                return None
    start = parse(start_date)
    end = parse(end_date)
    if start and now < start:
        return False
    if end and now > end:
        return False
    return True

async def scheduled_sender(app, target_chat_ids):
    try:
        print("定时消息调度器启动，目标:", target_chat_ids)
        while True:
            now = datetime.now()
            for chat_id in target_chat_ids:
                try:
                    schedules = await fetch_schedules(chat_id)
                except Exception as e:
                    print(f"查询群/频道 {chat_id} 的定时消息失败: {e}")
                    continue
                for sch in schedules:
                    if sch.get("status", 1) != 1:
                        continue
                    schedule_id = sch["id"]
                    repeat = sch.get("repeat_seconds", 0) or 60
                    period = sch.get("time_period", "")
                    if not _in_time_period(period, now):
                        continue
                    if not _in_date_range(sch.get("start_date", ""), sch.get("end_date", ""), now):
                        continue
                    last = last_sent.get(schedule_id)
                    if last and (now - last).total_seconds() < repeat:
                        continue
                    try:
                        text = sch.get("text", "")
                        media = sch.get("media_url", "")
                        media_type = sch.get("media_type", None)
                        # 构建按钮
                        button_text = sch.get("button_text", "")
                        button_url = sch.get("button_url", "")
                        markup = None
                        if button_text and button_url:
                            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                            markup = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url)]])
                        # 智能发送
                        if media:
                            msg = await send_media(app.bot, chat_id, media, caption=text, buttons=markup, media_type=media_type)
                            if not msg and text:
                                await app.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode=ParseMode.HTML)
                        elif text:
                            await app.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode=ParseMode.HTML)
                        last_sent[schedule_id] = now
                    except Exception as e:
                        print(f"定时消息发送到 {chat_id} 失败: {e}")
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("定时群发任务已取消，退出。")
