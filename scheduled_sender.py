import asyncio
import datetime
from db import fetch_schedules, update_schedule_multi, fetch_schedule
from modules.send_media import send_media, delete_message, pin_message

def parse_time_period(time_period: str):
    """解析时间段字符串，返回起止时间（时分）元组"""
    if not time_period:
        return None, None
    try:
        start_str, end_str = time_period.split("-")
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        return (start_h, start_m), (end_h, end_m)
    except Exception:
        return None, None

def check_in_period(now: datetime.datetime, time_period: str):
    """判断当前时间是否在指定时段内"""
    if not time_period:
        return True
    (start, end) = parse_time_period(time_period)
    if not start or not end:
        return True
    now_min = now.hour * 60 + now.minute
    start_min = start[0] * 60 + start[1]
    end_min = end[0] * 60 + end[1]
    if start_min <= end_min:
        return start_min <= now_min < end_min
    else:
        # 跨天
        return now_min >= start_min or now_min < end_min

def check_in_date(now: datetime.datetime, start_date: str, end_date: str):
    """判断当前日期是否在有效日期范围内"""
    fmt = "%Y-%m-%d %H:%M"
    fmt2 = "%Y-%m-%d"
    try:
        if start_date:
            sd = datetime.datetime.strptime(start_date, fmt if " " in start_date else fmt2)
            if now < sd:
                return False
        if end_date:
            ed = datetime.datetime.strptime(end_date, fmt if " " in end_date else fmt2)
            if now > ed:
                return False
        return True
    except Exception:
        return True

async def scheduled_sender(application, group_ids):
    """定时消息后台推送任务"""
    # 每个 schedule_id -> 最后推送时间
    last_sent = {}

    while True:
        now = datetime.datetime.now()
        for group_id in group_ids:
            schedules = await fetch_schedules(group_id)
            for sch in schedules:
                try:
                    # 检查启用状态
                    if not sch.get("status"):
                        continue
                    # 检查时间段
                    if not check_in_period(now, sch.get("time_period", "")):
                        continue
                    # 检查日期范围
                    if not check_in_date(now, sch.get("start_date", ""), sch.get("end_date", "")):
                        continue
                    # 检查周期
                    repeat_sec = sch.get("repeat_seconds", 0)
                    sid = sch["id"]
                    last = last_sent.get(sid, None)
                    # 取数据库的 last_sent_time 字段更稳妥（这里直接用内存字典）
                    if repeat_sec > 0 and last and (now - last).total_seconds() < repeat_sec:
                        continue
                    # 推送
                    text = sch.get("text", "")
                    media_url = sch.get("media_url", "")
                    media_type = sch.get("media_type", "")
                    button_text = sch.get("button_text", "")
                    button_url = sch.get("button_url", "")
                    buttons = None
                    if button_text and button_url:
                        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                        buttons = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url)]])
                    # 删除上一条
                    if sch.get("remove_last") and sch.get("last_message_id"):
                        try:
                            await delete_message(application.bot, group_id, sch["last_message_id"])
                        except Exception as e:
                            print(f"[scheduled_sender] 删除上一条失败: {e}")
                    msg = None
                    if media_url:
                        msg = await send_media(application.bot, group_id, media_url, caption=text, buttons=buttons, media_type=media_type)
                    else:
                        if buttons:
                            msg = await application.bot.send_message(chat_id=group_id, text=text, reply_markup=buttons)
                        else:
                            msg = await application.bot.send_message(chat_id=group_id, text=text)
                    # 置顶
                    if msg and sch.get("pin"):
                        try:
                            await pin_message(application.bot, group_id, msg.message_id)
                        except Exception as e:
                            print(f"[scheduled_sender] 置顶失败: {e}")
                    # 更新最后推送消息ID
                    if msg:
                        await update_schedule_multi(sid, last_message_id=msg.message_id)
                        last_sent[sid] = now
                except Exception as e:
                    print(f"[scheduled_sender] 定时消息推送异常: {e}")
        await asyncio.sleep(60)
