from db import (
    fetch_schedules, fetch_schedule, create_schedule,
    update_schedule, update_schedule_multi, delete_schedule
)
from modules.keyboards import schedule_list_menu, schedule_edit_menu
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

EDIT_TEXT, EDIT_MEDIA, EDIT_BUTTON, EDIT_REPEAT, EDIT_PERIOD, EDIT_DATE = range(6)

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
        await update.callback_query.edit_message_text("定时消息不存在。")
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
    await update.callback_query.edit_message_text(desc, reply_markup=schedule_edit_menu(schedule))

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "schedule_add":
        schedule_id = await create_schedule(update.effective_chat.id)
        await show_schedule_detail(update, context, schedule_id)
    elif data == "schedule_list":
        await show_schedule_list(update, context)
    elif data.startswith("edit_"):
        schedule_id = int(data.split("_")[1])
        await show_schedule_detail(update, context, schedule_id)
    elif data.startswith("toggle_status_"):
        schedule_id = int(data.split("_")[2])
        schedule = await fetch_schedule(schedule_id)
        await update_schedule(schedule_id, "status", not schedule['status'])
        await show_schedule_detail(update, context, schedule_id)
    elif data.startswith("toggle_remove_last_"):
        schedule_id = int(data.split("_")[3])
        schedule = await fetch_schedule(schedule_id)
        await update_schedule(schedule_id, "remove_last", not schedule['remove_last'])
        await show_schedule_detail(update, context, schedule_id)
    elif data.startswith("toggle_pin_"):
        schedule_id = int(data.split("_")[2])
        schedule = await fetch_schedule(schedule_id)
        await update_schedule(schedule_id, "pin", not schedule['pin'])
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
        await query.edit_message_text("请输入开始日期，格式如 2025-06-12：")
        return EDIT_DATE
    elif data.startswith("edit_end_date_"):
        schedule_id = int(data.split("_")[3])
        context.user_data["edit_schedule_id"] = schedule_id
        await query.edit_message_text("请输入结束日期，格式如 2025-06-30：")
        return EDIT_DATE + 1

    await query.answer()
    return ConversationHandler.END

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
    if period and not ("-" in period and len(period.split("-")) == 2):
        await update.message.reply_text("格式错误，示例：09:00-18:00 或留空全天")
        return EDIT_PERIOD
    await update_schedule(schedule_id, "time_period", period)
    await update.message.reply_text("时间段已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END

async def edit_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    date = update.message.text.strip()
    await update_schedule(schedule_id, "start_date", date)
    await update.message.reply_text("开始日期已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END

async def edit_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    date = update.message.text.strip()
    await update_schedule(schedule_id, "end_date", date)
    await update.message.reply_text("结束日期已更新。")
    await show_schedule_detail(update, context, schedule_id)
    return ConversationHandler.END
