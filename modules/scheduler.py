import pprint
import re
from db import (
    fetch_schedules, fetch_schedule, create_schedule,
    update_schedule, update_schedule_multi, delete_schedule
)
from modules.keyboards import schedule_list_menu, schedule_edit_menu, schedule_add_menu
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from datetime import datetime

# 状态枚举
(
    SELECT_GROUP, ADD_TEXT, ADD_MEDIA, ADD_BUTTON, ADD_REPEAT, 
    ADD_PERIOD, ADD_START_DATE, ADD_END_DATE, ADD_CONFIRM
) = range(200, 209)

# 可用群聊列表（可自己维护）
GROUPS = [
    {"chat_id": -1001234567890, "title": "群1"},
    {"chat_id": -1009876543210, "title": "群2"},
    # ... 你可以从数据库或配置文件动态维护
]

def group_select_menu():
    buttons = [
        [InlineKeyboardButton(g['title'], callback_data=f"set_group_{g['chat_id']}")]
        for g in GROUPS
    ]
    return InlineKeyboardMarkup(buttons)

def schedule_add_menu(step=None):
    if step == "confirm":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("保存", callback_data="confirm_save")],
            [InlineKeyboardButton("取消", callback_data="cancel_add")]
        ])
    return None

def parse_datetime_input(text):
    text = text.strip()
    if text in ["0", "留空", "不限"]:
        return ""
    m1 = re.match(r"^\d{4}-\d{2}-\d{2}$", text)
    m2 = re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$", text)
    if m1:
        return f"{text} 00:00"
    if m2:
        return text
    return None

# ========== 定时消息列表 ==========
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

# ========== 添加流程 ==========
async def entry_add_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("请选择要设置定时消息的群聊：", reply_markup=group_select_menu())
    return SELECT_GROUP

async def select_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("set_group_"):
        group_id = int(data[len("set_group_"):])
        context.user_data["selected_group_id"] = group_id
        await query.edit_message_text(f"已选择群聊：{group_id}，请继续设置定时消息。\n请输入文本内容：")
        context.user_data["new_schedule"] = {}
        return ADD_TEXT
    await query.answer("请选择群聊")
    return SELECT_GROUP

async def add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_schedule']['text'] = text
    await update.message.reply_text("请发送媒体（图片/视频/文件ID/URL），或输入“无”跳过：")
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
    await update.message.reply_text("请输入按钮文字和链接，用英文逗号分隔，如：更多内容,https://example.com\n如无需按钮请输入“无”：")
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
    await update.message.reply_text("请输入重复时间，单位分钟（如60）：")
    return ADD_REPEAT

async def add_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text.strip())
        context.user_data['new_schedule']['repeat_seconds'] = minutes * 60
    except Exception:
        await update.message.reply_text("请输入整数分钟数。")
        return ADD_REPEAT
    await update.message.reply_text("请输入时间段，格式如 09:00-18:00 或留空全天：")
    return ADD_PERIOD

async def add_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    period = update.message.text.strip()
    if period in ["0", "留空", "不限", ""]:
        period = ""
    elif not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", period):
        await update.message.reply_text("格式错误，示例：09:00-18:00 或留空全天")
        return ADD_PERIOD
    context.user_data['new_schedule']['time_period'] = period
    await update.message.reply_text("请输入开始日期，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限：")
    return ADD_START_DATE

async def add_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    dt = parse_datetime_input(text)
    if dt is None:
        await update.message.reply_text("格式错误，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限。")
        return ADD_START_DATE
    context.user_data['new_schedule']['start_date'] = dt
    await update.message.reply_text("请输入结束日期，格式如 2025-06-30 或 2025-06-30 23:59，或留空不限：")
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
        "请点击“保存”按钮确认添加，或点击“取消”放弃。"
    )
    await update.message.reply_text(desc, reply_markup=schedule_add_menu(step="confirm"))
    return ADD_CONFIRM

async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "confirm_save":
        group_id = context.user_data.get('selected_group_id')
        sch = context.user_data.get('new_schedule')
        if not group_id or not sch:
            await query.edit_message_text("群聊或消息内容缺失，无法保存。")
            return ConversationHandler.END
        await create_schedule(group_id, sch)
        await query.edit_message_text("定时消息已添加。")
        context.user_data.pop("new_schedule", None)
        context.user_data.pop("selected_group_id", None)
        return ConversationHandler.END
    elif query.data == "cancel_add":
        await query.edit_message_text("已取消添加。")
        context.user_data.pop("new_schedule", None)
        context.user_data.pop("selected_group_id", None)
        return ConversationHandler.END
    else:
        await query.answer("未知操作")
        return ADD_CONFIRM

async def add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in ["保存", "确认"]:
        group_id = context.user_data.get('selected_group_id')
        sch = context.user_data['new_schedule']
        await create_schedule(group_id, sch)
        await update.message.reply_text("定时消息已添加。")
        context.user_data.pop("new_schedule", None)
        context.user_data.pop("selected_group_id", None)
        return ConversationHandler.END
    elif text in ["取消"]:
        await update.message.reply_text("已取消添加。")
        context.user_data.pop("new_schedule", None)
        context.user_data.pop("selected_group_id", None)
        return ConversationHandler.END
    else:
        await update.message.reply_text("请点击“保存”按钮确认添加，或点击“取消”放弃。")
        return ADD_CONFIRM

# ========== 定时推送 ==========
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
    group_ids = [g['chat_id'] for g in GROUPS]
    for chat_id in group_ids:
        schedules = await fetch_schedules(chat_id)
        for sch in schedules:
            if is_schedule_active(sch):
                try:
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
                except Exception as e:
                    print(f"推送到群{chat_id}出错：", e)

def schedule_broadcast_jobs(application):
    application.job_queue.run_repeating(
        broadcast_task,
        interval=60,   # 每60秒执行一次
        first=10       # 启动后10秒首次执行
    )

# ========== ConversationHandler ==========
def get_scheduler_conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^添加定时消息$"), entry_add_schedule)],
        states={
            SELECT_GROUP: [CallbackQueryHandler(select_group_callback)],
            ADD_TEXT: [MessageHandler(filters.TEXT, add_text)],
            ADD_MEDIA: [MessageHandler(filters.ALL, add_media)],
            ADD_BUTTON: [MessageHandler(filters.TEXT, add_button)],
            ADD_REPEAT: [MessageHandler(filters.TEXT, add_repeat)],
            ADD_PERIOD: [MessageHandler(filters.TEXT, add_period)],
            ADD_START_DATE: [MessageHandler(filters.TEXT, add_start_date)],
            ADD_END_DATE: [MessageHandler(filters.TEXT, add_end_date)],
            ADD_CONFIRM: [
                MessageHandler(filters.TEXT, add_confirm),
                CallbackQueryHandler(confirm_callback)
            ]
        },
        fallbacks=[],
        allow_reentry=True
    )
