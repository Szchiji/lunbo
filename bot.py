import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
ADMINS = set(int(i) for i in os.getenv("ADMINS").split(","))

PHOTO_VIDEO, TEXT, BUTTONS, INTERVAL, START_STOP, CONFIRM = range(6)

scheduler = AsyncIOScheduler()
user_data = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("抱歉，您不是管理员，无权限使用此命令。")
            return
        return await func(update, context)
    return wrapper

@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用定时发送机器人！\n请发送 /add 开始添加定时消息。")

@admin_only
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.clear()
    await update.message.reply_text("请发送一张图片或视频。")
    return PHOTO_VIDEO

@admin_only
async def photo_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.photo:
        user_data['media_type'] = 'photo'
        user_data['media_id'] = msg.photo[-1].file_id
    elif msg.video:
        user_data['media_type'] = 'video'
        user_data['media_id'] = msg.video.file_id
    else:
        await update.message.reply_text("请发送一张图片或视频！")
        return PHOTO_VIDEO
    await update.message.reply_text("请输入文字内容（可以为空）。")
    return TEXT

@admin_only
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['text'] = update.message.text or ""
    await update.message.reply_text(
        "是否添加按钮？\n格式：按钮文字|按钮链接\n如果不需要按钮，回复“跳过”。"
    )
    return BUTTONS

@admin_only
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == '跳过':
        user_data['buttons'] = []
    else:
        try:
            btn_text, btn_url = text.split('|', 1)
            user_data['buttons'] = [[InlineKeyboardButton(btn_text.strip(), url=btn_url.strip())]]
        except Exception:
            await update.message.reply_text("格式错误，请输入：按钮文字|按钮链接，或者回复“跳过”。")
            return BUTTONS
    await update.message.reply_text("请输入发送间隔时间（单位：小时，整数），例如 3 。")
    return INTERVAL

@admin_only
async def interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        hours = int(update.message.text)
        if hours < 1:
            raise ValueError
        user_data['interval_hours'] = hours
    except Exception:
        await update.message.reply_text("请输入合法的整数小时，且不小于1。")
        return INTERVAL
    await update.message.reply_text(
        "请输入开始时间和停止时间，格式为：\nYYYY-MM-DD HH:MM YYYY-MM-DD HH:MM\n例如：2025-05-30 14:00 2025-06-05 20:00"
    )
    return START_STOP

@admin_only
async def start_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        parts = text.split()
        if len(parts) != 4:
            raise ValueError("参数数量不正确")
        start_str = parts[0] + " " + parts[1]
        stop_str = parts[2] + " " + parts[3]
        start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        stop_time = datetime.strptime(stop_str, "%Y-%m-%d %H:%M")
        if stop_time <= start_time:
            await update.message.reply_text("停止时间必须晚于开始时间，请重新输入。")
            return START_STOP
        user_data['start_time'] = start_time
        user_data['stop_time'] = stop_time
    except Exception:
        await update.message.reply_text(
            "格式错误，请输入开始和停止时间，格式如：\n2025-05-30 14:00 2025-06-05 20:00"
        )
        return START_STOP

    reply_text = f"请确认以下信息：\n\n" \
                 f"媒体类型: {user_data['media_type']}\n" \
                 f"文字内容: {user_data['text']}\n" \
                 f"按钮: {'有' if user_data['buttons'] else '无'}\n" \
                 f"发送间隔: {user_data['interval_hours']} 小时\n" \
                 f"开始时间: {user_data['start_time']}\n" \
                 f"停止时间: {user_data['stop_time']}\n\n" \
                 f"确认发送请输入“确认”，取消请输入“取消”。"
    await update.message.reply_text(reply_text)
    return CONFIRM

@admin_only
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == '确认':
        context.user_data['schedule'] = user_data.copy()
        await update.message.reply_text("定时发送已设置，机器人将按计划发送消息。")
        schedule_job(context)
        return ConversationHandler.END
    elif text == '取消':
        await update.message.reply_text("已取消。")
        return ConversationHandler.END
    else:
        await update.message.reply_text("请输入“确认”或“取消”。")
        return CONFIRM

def schedule_job(context: ContextTypes.DEFAULT_TYPE):
    schedule = context.user_data['schedule']

    # 先清理之前所有任务，保证只保留最新任务
    for job in scheduler.get_jobs():
        job.remove()

    async def job_send():
        now = datetime.now()
        if schedule['start_time'] <= now <= schedule['stop_time']:
            buttons = InlineKeyboardMarkup(schedule['buttons']) if schedule['buttons'] else None
            try:
                if schedule['media_type'] == 'photo':
                    await context.bot.send_photo(chat_id=CHAT_ID, photo=schedule['media_id'], caption=schedule['text'], reply_markup=buttons)
                else:
                    await context.bot.send_video(chat_id=CHAT_ID, video=schedule['media_id'], caption=schedule['text'], reply_markup=buttons)
            except Exception as e:
                print(f"发送失败: {e}")
        else:
            print("当前时间不在自定义时间区间，跳过发送")

    scheduler.add_job(job_send, 'interval', hours=schedule['interval_hours'])
    if not scheduler.running:
        scheduler.start()

@admin_only
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("已取消操作。")
    return ConversationHandler.END

@admin_only
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("用法: /addadmin <用户ID>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("请输入正确的用户ID。")
        return

    if user_id in ADMINS:
        await update.message.reply_text("该用户已经是管理员。")
        return

    ADMINS.add(user_id)
    await update.message.reply_text(f"成功添加管理员：{user_id}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add)],
        states={
            PHOTO_VIDEO: [MessageHandler(filters.PHOTO | filters.VIDEO, photo_video)],
            TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, text)],
            BUTTONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, buttons)],
            INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, interval)],
            START_STOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_stop)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('addadmin', add_admin))
    app.add_handler(conv_handler)

    global scheduler
    scheduler.start()

    print("机器人已启动")
    app.run_polling()

if __name__ == '__main__':
    main()
