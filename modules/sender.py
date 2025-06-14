import asyncio
from datetime import datetime, time as dtime
from db import fetch_schedules
from modules.sender import send_text, send_media, build_buttons
from telegram.constants import ParseMode

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
                    print(f"[scheduled_sender] 查询群/频道 {chat_id} 的定时消息失败: {e}")
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
                        media_type = sch.get("media_type")     # 新增字段
                        buttons = sch.get("button_json") or sch.get("buttons") or None
                        markup = build_buttons(buttons) if buttons else None

                        if media:
                            # 智能发送媒体（支持 file_id/直链，并自动 media_type 区分）
                            msg = await send_media(
                                app.bot,
                                chat_id,
                                media,
                                caption=text,
                                buttons=markup,
                                media_type=media_type
                            )
                            # 如果媒体发送失败，fallback 发送文本
                            if not msg and text:
                                await send_text(app.bot, chat_id, text, buttons=markup, parse_mode=ParseMode.HTML)
                        elif text:
                            await send_text(app.bot, chat_id, text, buttons=markup, parse_mode=ParseMode.HTML)
                        else:
                            continue
                        last_sent[schedule_id] = now
                    except Exception as e:
                        print(f"[scheduled_sender] 发送消息失败: {e}")
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("定时群发任务已取消，退出。")
