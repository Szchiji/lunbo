import pprint
import re
from db import (
    fetch_schedules, fetch_schedule, create_schedule,
    update_schedule, update_schedule_multi, delete_schedule
)
from modules.keyboards import schedule_list_menu, schedule_edit_menu, schedule_add_menu
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

EDIT_TEXT, EDIT_MEDIA, EDIT_BUTTON, EDIT_REPEAT, EDIT_PERIOD, EDIT_DATE = range(6)
ADD_TEXT, ADD_MEDIA, ADD_BUTTON, ADD_REPEAT, ADD_PERIOD, ADD_START_DATE, ADD_END_DATE, ADD_CONFIRM = range(100, 108)  # 8 items

def parse_datetime_input(text):
    """
    支持 YYYY-MM-DD 或 YYYY-MM-DD HH:MM
    返回标准字符串或空字符串
    """
    text = text.strip()
    if text in ["0", "留空", "不限"]:
        return ""
    m1 = re.match(r"^\d{4}-\d{2}-\d{2}$", text)
    m2 = re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$", text)
    if m1:
        return f"{text} 00:00"
    if m2:
        return text
    return None  # 格式不对

async def show_schedule_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    schedules = await fetch_schedules(chat_id)
    if update.message:
        await update.message.reply_text(
            "⏰ 定时消息列表：\n点击条目可设置。",
            reply_markup=schedule_list_menu(schedules)
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "⏰ 定时消息列表：\n点击条目可设置。",
            reply_markup=schedule_list_menu(schedules)
        )

async def show_schedule_detail(update, context, schedule_id):
    schedule = await fetch_schedule(schedule_id)
    if not schedule:
        if hasattr(update, "callback_query") and update.callback_query:
            await update.callback_query.edit_message_text("定时消息不存在。")
        elif hasattr(update, "message") and update.message:
            await update.message.reply_text("定时消息不存在。")
        return
    desc = (
        f"⏰ 定时消息\n"
        f"状态: {'✅启用' if schedule['status'] else '❌关闭'}\n"
        f"重复: 每{schedule['repeat_seconds']//60}分钟\n"
        f"删除上一条: {'是' if schedule['remove_last'] else '否'}\n"
        f"置顶: {'是' if schedule['pin'] else '否'}\n"
        f"媒体: {'✔️' if schedule['media_url'] else '✖️'}\n"
        f"链接按钮: {'✔️' if schedule['button_text'] else '✖️'}\n"
        f"文本内容:\n{schedule['text']}\n"
        f"时间段: {schedule['time_period'] or '全天'}\n"
        f"日期: {schedule['start_date'] or '--'} ~ {schedule['end_date'] or '--'}"
    )
    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(desc, reply_markup=schedule_edit_menu(schedule))
    elif hasattr(update, "message") and update.message:
        await update.message.reply_text(desc, reply_markup=schedule_edit_menu(schedule))

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "add_schedule":
        context.user_data["new_schedule"] = {}
        await query.edit_message_text("【添加定时消息】\n请输入文本内容：", reply_markup=schedule_add_menu(step="text"))
        return ADD_TEXT
    elif data == "schedule_list":
        await show_schedule_list(update, context)
    elif data.startswith("edit_") and not any(data.startswith(f"edit_{t}_") for t in ["text", "media", "button", "repeat", "time_period", "start_date", "end_date"]):
        schedule_id = int(data.split("_")[1])
        await show_schedule_detail(update, context, schedule_id)
        return ConversationHandler.END
    elif data.startswith("toggle_status_"):
        schedule_id = int(data.split("_")[2])
        schedule = await fetch_schedule(schedule_id)
        await update_schedule(schedule_id, "status", 0 if schedule['status'] else 1)
        await show_schedule_detail(update, context, schedule_id)
    elif data.startswith("toggle_remove_last_"):
        schedule_id = int(data.split("_")[3])
        schedule = await fetch_schedule(schedule_id)
        await update_schedule(schedule_id, "remove_last", 0 if schedule['remove_last'] else 1)
        await show_schedule_detail(update, context, schedule_id)
    elif data.startswith("toggle_pin_"):
        schedule_id = int(data.split("_")[2])
        schedule = await fetch_schedule(schedule_id)
        await update_schedule(schedule_id, "pin", 0 if schedule['pin'] else 1)
        await show_schedule_detail(update, context, schedule_id)
    elif data.startswith("delete_"):
        schedule_id = int(data.split("_")[1])
        await delete_schedule(schedule_id)
        await show_schedule_list(update, context)
    elif data.startswith("edit_text_"):
        schedule_id = int(data.split("_")[2])
        context.user_data["edit_schedule_id"] = schedule_id
        await query.edit_message_text("请输入新的文本内容：")
        return EDIT_TEXT
    elif data.startswith("edit_media_"):
        schedule_id = int(data.split("_")[2])
        context.user_data["edit_schedule_id"] = schedule_id
        await query.edit_message_text("请发送图片或视频（Telegram链接/文件ID/图片URL）：")
        return EDIT_MEDIA
    elif data.startswith("edit_button_"):
        schedule_id = int(data.split("_")[2])
        context.user_data["edit_schedule_id"] = schedule_id
        await query.edit_message_text("请输入按钮文字和链接（用英文逗号分隔，如：更多内容,https://example.com）：")
        return EDIT_BUTTON
    elif data.startswith("edit_repeat_"):
        schedule_id = int(data.split("_")[2])
        context.user_data["edit_schedule_id"] = schedule_id
        await query.edit_message_text("请输入重复间隔，单位分钟（如60）：")
        return EDIT_REPEAT
    elif data.startswith("edit_time_period_"):
        schedule_id = int(data.split("_")[3])
        context.user_data["edit_schedule_id"] = schedule_id
        await query.edit_message_text("请输入时间段，格式如 09:00-18:00 或留空全天：")
        return EDIT_PERIOD
    elif data.startswith("edit_start_date_"):
        schedule_id = int(data.split("_")[3])
        context.user_data["edit_schedule_id"] = schedule_id
        await query.edit_message_text("请输入开始日期，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限：")
        return EDIT_DATE
    elif data.startswith("edit_end_date_"):
        schedule_id = int(data.split("_")[3])
        context.user_data["edit_schedule_id"] = schedule_id
        await query.edit_message_text("请输入结束日期，格式如 2025-06-30 或 2025-06-30 23:59，或留空不限：")
        return EDIT_DATE + 1
    elif data == "cancel_add":
        await query.edit_message_text("已取消添加。")
        context.user_data.pop("new_schedule", None)
        await show_schedule_list(update, context)
        return ConversationHandler.END

    await query.answer()
    return ConversationHandler.END

# ========== 添加流程 ==========
async def add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_schedule']['text'] = text
    await update.message.reply_text("请发送媒体（图片/视频/文件ID/URL），或输入“无”跳过：", reply_markup=schedule_add_menu(step="media"))
    return ADD_MEDIA

async def add_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        media = update.message.photo[-1].file_id
    elif update.message.video:
        media = update.message.video.file_id
    elif update.message.text and update.message.text.strip().lower() != "无":
        media = update.message.text.strip()
    else:
        media = ""
    context.user_data['new_schedule']['media_url'] = media
    await update.message.reply_text("请输入按钮文字和链接，用英文逗号分隔，如：更多内容,https://example.com\n如无需按钮请输入“无”：", reply_markup=schedule_add_menu(step="button"))
    return ADD_BUTTON

async def add_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "无":
        context.user_data['new_schedule']['button_text'] = ""
        context.user_data['new_schedule']['button_url'] = ""
    else:
        try:
            btn_text, btn_url = text.split(",", 1)
            context.user_data['new_schedule']['button_text'] = btn_text.strip()
            context.user_data['new_schedule']['button_url'] = btn_url.strip()
        except Exception:
            await update.message.reply_text("格式错误，请用英文逗号隔开，如：按钮文字,https://xxx.com\n如无需按钮请输入“无”。")
            return ADD_BUTTON
    await update.message.reply_text("请输入重复时间，单位分钟（如60）：", reply_markup=schedule_add_menu(step="repeat"))
    return ADD_REPEAT

async def add_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text.strip())
        context.user_data['new_schedule']['repeat_seconds'] = minutes * 60
    except Exception:
        await update.message.reply_text("请输入整数分钟数。")
        return ADD_REPEAT
    await update.message.reply_text("请输入时间段，格式如 09:00-18:00 或留空全天：", reply_markup=schedule_add_menu(step="period"))
    return ADD_PERIOD

async def add_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    period = update.message.text.strip()
    if period in ["0", "留空", "不限", ""]:
        period = ""
    elif not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", period):
        await update.message.reply_text("格式错误，示例：09:00-18:00 或留空全天")
        return ADD_PERIOD
    context.user_data['new_schedule']['time_period'] = period
    await update.message.reply_text("请输入开始日期，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限：", reply_markup=schedule_add_menu(step="start"))
    return ADD_START_DATE

async def add_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    dt = parse_datetime_input(text)
    if dt is None:
        await update.message.reply_text("格式错误，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限。")
        return ADD_START_DATE
    context.user_data['new_schedule']['start_date'] = dt
    await update.message.reply_text("请输入结束日期，格式如 2025-06-30 或 2025-06-30 23:59，或留空不限：", reply_markup=schedule_add_menu(step="end"))
    return ADD_END_DATE

async def add_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    dt = parse_datetime_input(text)
    if dt is None:
        await update.message.reply_text("格式错误，格式如 2025-06-30 或 2025-06-30 23:59，或留空不限。")
        return ADD_END_DATE
    context.user_data['new_schedule']['end_date'] = dt
    sch = context.user_data['new_schedule']
    desc = (
        "【确认添加定时消息】\n"
        f"文本：{sch.get('text','')}\n"
        f"媒体：{'✔️' if sch.get('media_url') else '✖️'}\n"
        f"按钮：{('✔️' if sch.get('button_text') else '✖️')}\n"
        f"重复：每{sch.get('repeat_seconds',0)//60}分钟\n"
        f"时间段：{sch.get('time_period','全天')}\n"
        f"日期：{sch.get('start_date','--')} ~ {sch.get('end_date','--')}\n\n"
        "请发送“保存”确认添加，或发送“取消”放弃。"
    )
    await update.message.reply_text(desc, reply_markup=schedule_add_menu(step="confirm"))
    return ADD_CONFIRM

async def add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in ["保存", "确认"]:
        chat_id = update.effective_chat.id
        sch = context.user_data['new_schedule']
        print("DEBUG: chat_id =", chat_id)
        print("DEBUG: sch =")
        pprint.pprint(sch)
        await create_schedule(chat_id, sch)
        print("DEBUG: create_schedule已调用")
        await update.message.reply_text("定时消息已添加。")
        await show_schedule_list(update, context)
        context.user_data.pop("new_schedule", None)
        return ConversationHandler.END
    elif text in ["取消"]:
        await update.message.reply_text("已取消添加。")
        context.user_data.pop("new_schedule", None)
        await show_schedule_list(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("请发送“保存”确认添加，或发送“取消”放弃。")
        return ADD_CONFIRM

# ========== 编辑流程 ==========

async def edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    if not schedule_id:
        await update.message.reply_text("未找到要编辑的定时消息。")
        return ConversationHandler.END
    await update_schedule(schedule_id, "text", update.message.text.strip())
    await update.message.reply_text("文本内容已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END

async def edit_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.video:
        file_id = update.message.video.file_id
    elif update.message.text and update.message.text.startswith("http"):
        file_id = update.message.text.strip()
    if not file_id:
        await update.message.reply_text("请发送图片、视频或文件ID/URL。")
        return EDIT_MEDIA
    await update_schedule(schedule_id, "media_url", file_id)
    await update.message.reply_text("媒体内容已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END

async def edit_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    try:
        txt, url = update.message.text.strip().split(",", 1)
    except Exception:
        await update.message.reply_text("格式错误，请用英文逗号隔开，如：按钮文字,https://xxx.com")
        return EDIT_BUTTON
    await update_schedule_multi(schedule_id, {"button_text": txt.strip(), "button_url": url.strip()})
    await update.message.reply_text("按钮已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END

async def edit_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    try:
        minutes = int(update.message.text.strip())
        seconds = minutes * 60
    except Exception:
        await update.message.reply_text("请输入整数分钟数。")
        return EDIT_REPEAT
    await update_schedule(schedule_id, "repeat_seconds", seconds)
    await update.message.reply_text("重复时间已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END

async def edit_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    period = update.message.text.strip()
    if period in ["0", "留空", "不限", ""]:
        period = ""
    elif not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", period):
        await update.message.reply_text("格式错误，示例：09:00-18:00 或留空全天")
        return EDIT_PERIOD
    await update_schedule(schedule_id, "time_period", period)
    await update.message.reply_text("时间段已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END

async def edit_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    text = update.message.text.strip()
    dt = parse_datetime_input(text)
    if dt is None:
        await update.message.reply_text("格式错误，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限。")
        return EDIT_DATE
    await update_schedule(schedule_id, "start_date", dt)
    await update.message.reply_text("开始日期已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END

async def edit_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    text = update.message.text.strip()
    dt = parse_datetime_input(text)
    if dt is None:
        await update.message.reply_text("格式错误，格式如 2025-06-30 或 2025-06-30 23:59，或留空不限。")
        return EDIT_DATE + 1
    await update_schedule(schedule_id, "end_date", dt)
    await update.message.reply_text("结束日期已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END
