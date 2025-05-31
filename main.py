import os
import logging
import sqlite3
import json
from uuid import uuid4
from datetime import datetime, timedelta

from flask import Flask, request

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# --- 日志配置 ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 环境变量 ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Render 需配置此项
PORT = int(os.getenv("PORT", "8443"))
IS_RENDER = os.getenv("RENDER", "").lower() == "true"

# --- Flask App ---
app = Flask(__name__)

# --- SQLite DB ---
DB_PATH = "schedule_tasks.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL,
                message_type TEXT NOT NULL,
                content TEXT,
                file_id TEXT,
                buttons TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """
        )
        conn.commit()


# --- 定时任务调度 ---
scheduler = BackgroundScheduler()
scheduler.start()


def load_tasks():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE active=1")
        rows = cursor.fetchall()
        tasks = []
        for row in rows:
            task = {
                "id": row[0],
                "chat_id": row[1],
                "start_time": row[2],
                "end_time": row[3],
                "interval_minutes": row[4],
                "message_type": row[5],
                "content": row[6],
                "file_id": row[7],
                "buttons": json.loads(row[8]) if row[8] else [],
                "active": bool(row[9]),
                "created_at": row[10],
            }
            tasks.append(task)
        return tasks


def send_scheduled_message(context: CallbackContext):
    job_data = context.job.context
    bot = context.bot
    chat_id = job_data["chat_id"]
    message_type = job_data["message_type"]
    content = job_data["content"]
    file_id = job_data["file_id"]
    buttons = job_data["buttons"]

    keyboard = []
    for btn in buttons:
        keyboard.append(
            InlineKeyboardButton(text=btn["text"], url=btn.get("url", None), callback_data=btn.get("callback_data"))
        )
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None

    try:
        if message_type == "photo":
            bot.send_photo(chat_id=chat_id, photo=file_id, caption=content, reply_markup=reply_markup)
        elif message_type == "video":
            bot.send_video(chat_id=chat_id, video=file_id, caption=content, reply_markup=reply_markup)
        else:
            bot.send_message(chat_id=chat_id, text=content, reply_markup=reply_markup)
        logger.info(f"消息发送成功，任务ID：{job_data['id']}")
    except Exception as e:
        logger.error(f"发送失败，任务ID：{job_data['id']}，错误：{e}")


def schedule_task(task):
    start_dt = datetime.strptime(task["start_time"], "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(task["end_time"], "%Y-%m-%d %H:%M")
    now = datetime.now()

    if now > end_dt:
        logger.info(f"任务过期，不调度，任务ID：{task['id']}")
        return

    # 从start_time的下一个时间点开始执行定时任务，间隔为interval_minutes
    first_run = max(now, start_dt)

    def job_wrapper(context: CallbackContext):
        current_time = datetime.now()
        if current_time > end_dt:
            logger.info(f"任务结束，取消调度，任务ID：{task['id']}")
            context.job.schedule_removal()
        else:
            send_scheduled_message(context)

    scheduler.add_job(
        job_wrapper,
        trigger=IntervalTrigger(minutes=task["interval_minutes"], start_date=first_run, end_date=end_dt),
        id=task["id"],
        replace_existing=True,
        args=[],
        kwargs={},
        misfire_grace_time=60,
        max_instances=1,
        coalesce=True,
        # context传入任务信息
        context=task,
    )
    logger.info(f"任务调度已设置，任务ID：{task['id']}")


def reload_all_schedules():
    scheduler.remove_all_jobs()
    tasks = load_tasks()
    for task in tasks:
        schedule_task(task)


# --- Telegram Bot 交互状态 ---
(
    TYPE_SELECT,
    WAITING_MEDIA,
    WAITING_TEXT,
    WAITING_BUTTONS,
    WAITING_START,
    WAITING_END,
    WAITING_INTERVAL,
    CONFIRMATION,
) = range(8)

user_data = {}


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "欢迎使用定时消息Bot！\n"
        "使用 /addtask 添加新任务，/listtasks 查看任务，/deletetask 删除任务，/edittask 修改任务。"
    )


def addtask(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_data[chat_id] = {
        "id": str(uuid4()),
        "chat_id": chat_id,
        "message_type": None,
        "content": "",
        "file_id": None,
        "buttons": [],
        "start_time": None,
        "end_time": None,
        "interval_minutes": None,
    }
    update.message.reply_text(
        "请先选择消息类型:\n1 - 文字\n2 - 图片\n3 - 视频\n发送对应数字选择。"
    )
    return TYPE_SELECT


def type_select(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    if text == "1":
        user_data[chat_id]["message_type"] = "text"
        update.message.reply_text("请发送消息文本内容：")
        return WAITING_TEXT
    elif text == "2":
        user_data[chat_id]["message_type"] = "photo"
        update.message.reply_text("请发送图片：")
        return WAITING_MEDIA
    elif text == "3":
        user_data[chat_id]["message_type"] = "video"
        update.message.reply_text("请发送视频：")
        return WAITING_MEDIA
    else:
        update.message.reply_text("无效输入，请输入数字 1 / 2 / 3。")
        return TYPE_SELECT


def waiting_media(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    msg_type = user_data[chat_id]["message_type"]
    file_id = None
    if msg_type == "photo" and update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif msg_type == "video" and update.message.video:
        file_id = update.message.video.file_id
    else:
        update.message.reply_text("发送的媒体类型与选择不匹配，请重新发送。")
        return WAITING_MEDIA

    user_data[chat_id]["file_id"] = file_id
    update.message.reply_text("请发送消息文字内容（可以为空，直接发送空行或点 . 表示无文字）：")
    return WAITING_TEXT


def waiting_text(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text or ""
    if text == ".":
        text = ""
    user_data[chat_id]["content"] = text
    update.message.reply_text(
        "是否添加按钮？\n发送格式示例：\n[按钮文字](按钮链接)\n发送多行多个按钮，发送 /done 结束添加按钮\n发送 /skip 跳过按钮添加"
    )
    user_data[chat_id]["buttons"] = []
    return WAITING_BUTTONS


def waiting_buttons(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    if text == "/done":
        if not user_data[chat_id]["buttons"]:
            update.message.reply_text("未添加任何按钮，跳过。")
        update.message.reply_text("请输入开始时间 (格式: YYYY-MM-DD HH:MM)，例如：2025-06-01 12:00")
        return WAITING_START
    elif text == "/skip":
        update.message.reply_text("跳过按钮添加。请输入开始时间 (格式: YYYY-MM-DD HH:MM)，例如：2025-06-01 12:00")
        return WAITING_START
    else:
        # 解析按钮格式 [按钮文字](按钮链接)
        import re

        pattern = r"\[(.*?)\]\((.*?)\)"
        matches = re.findall(pattern, text)
        if matches:
            for t, url in matches:
                user_data[chat_id]["buttons"].append({"text": t, "url": url})
            update.message.reply_text(f"已添加按钮：{', '.join(t for t, u in matches)}。继续添加或发送 /done 完成。")
        else:
            update.message.reply_text("格式错误，请使用 [按钮文字](按钮链接) 格式，或发送 /done 完成添加。")
        return WAITING_BUTTONS


def waiting_start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    try:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        if dt < datetime.now():
            update.message.reply_text("开始时间不能早于当前时间，请重新输入。")
            return WAITING_START
        user_data[chat_id]["start_time"] = text
        update.message.reply_text("请输入结束时间 (格式: YYYY-MM-DD HH:MM)，例如：2025-06-02 12:00")
        return WAITING_END
    except ValueError:
        update.message.reply_text("格式错误，请输入正确的时间格式 YYYY-MM-DD HH:MM。")
        return WAITING_START


def waiting_end(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    try:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        start_dt = datetime.strptime(user_data[chat_id]["start_time"], "%Y-%m-%d %H:%M")
        if dt <= start_dt:
            update.message.reply_text("结束时间必须晚于开始时间，请重新输入。")
            return WAITING_END
        user_data[chat_id]["end_time"] = text
        update.message.reply_text("请输入发送间隔（分钟），例如：180 表示每3小时发送一次")
        return WAITING_INTERVAL
    except ValueError:
        update.message.reply_text("格式错误，请输入正确的时间格式 YYYY-MM-DD HH:MM。")
        return WAITING_END


def waiting_interval(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    if not text.isdigit():
        update.message.reply_text("请输入有效数字，发送间隔（分钟）。")
        return WAITING_INTERVAL
    interval = int(text)
    if interval < 1:
        update.message.reply_text("发送间隔必须大于0。")
        return WAITING_INTERVAL
    user_data[chat_id]["interval_minutes"] = interval

    # 预览确认消息
    task = user_data[chat_id]
    preview_msg = f"请确认任务内容：\n" \
                  f"类型：{task['message_type']}\n" \
                  f"文字内容：{task['content'] or '[无]'}\n" \
                  f"开始时间：{task['start_time']}\n" \
                  f"结束时间：{task['end_time']}\n" \
                  f"发送间隔：{task['interval_minutes']} 分钟\n" \
                  f"按钮数量：{len(task['buttons'])}\n\n" \
                  f"确认发送请回复 /confirm ，取消请回复 /cancel 。"
    update.message.reply_text(preview_msg)
    return CONFIRMATION


def confirmation(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    if text == "/confirm":
        task = user_data.get(chat_id)
        if not task:
            update.message.reply_text("无任务数据，取消。")
            return ConversationHandler.END

        # 保存数据库
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tasks (id, chat_id, start_time, end_time, interval_minutes, message_type, content, file_id, buttons, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    task["id"],
                    str(task["chat_id"]),
                    task["start_time"],
                    task["end_time"],
                    task["interval_minutes"],
                    task["message_type"],
                    task["content"],
                    task["file_id"],
                    json.dumps(task["buttons"]),
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                ),
            )
            conn.commit()

        reload_all_schedules()

        update.message.reply_text("任务已保存并启用！", reply_markup=ReplyKeyboardRemove())
        user_data.pop(chat_id, None)
        return ConversationHandler.END
    elif text == "/cancel":
        update.message.reply_text("任务创建取消。", reply_markup=ReplyKeyboardRemove())
        user_data.pop(chat_id, None)
        return ConversationHandler.END
    else:
        update.message.reply_text("请发送 /confirm 确认或 /cancel 取消。")
        return CONFIRMATION


def cancel(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_data.pop(chat_id, None)
    update.message.reply_text("操作已取消。", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def listtasks(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, start_time, end_time, interval_minutes, message_type, active FROM tasks WHERE chat_id=?",
            (str(chat_id),),
        )
        rows = cursor.fetchall()
        if not rows:
            update.message.reply_text("您当前没有任何任务。")
            return

        msg_lines = ["您的任务列表："]
        for r in rows:
            status = "启用" if r[5] else "已禁用"
            msg_lines.append(
                f"任务ID: {r[0]}\n类型: {r[4]}, 开始: {r[1]}, 结束: {r[2]}, 间隔(分钟): {r[3]}, 状态: {status}\n"
            )
        update.message.reply_text("\n".join(msg_lines))


def deletetask(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    args = context.args
    if not args:
        update.message.reply_text("请在命令后跟任务ID，例如：/deletetask 任务ID")
        return
    task_id = args[0]
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM tasks WHERE id=? AND chat_id=?",
            (task_id, str(chat_id)),
        )
        row = cursor.fetchone()
        if not row:
            update.message.reply_text("未找到对应任务。")
            return
        cursor.execute(
            "UPDATE tasks SET active=0 WHERE id=?",
            (task_id,),
        )
        conn.commit()
    reload_all_schedules()
    update.message.reply_text(f"任务 {task_id} 已删除（禁用）。")


# --- Telegram Webhook & Polling ---

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"


if __name__ == "__main__":
    init_db()

    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    bot = updater.bot

    # 加载已有任务调度
    reload_all_schedules()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("addtask", addtask)],
        states={
            TYPE_SELECT: [MessageHandler(Filters.text & ~Filters.command, type_select)],
            WAITING_MEDIA: [MessageHandler(Filters.photo | Filters.video, waiting_media)],
            WAITING_TEXT: [MessageHandler(Filters.text & ~Filters.command, waiting_text)],
            WAITING_BUTTONS: [MessageHandler(Filters.text & ~Filters.command, waiting_buttons)],
            WAITING_START: [MessageHandler(Filters.text & ~Filters.command, waiting_start)],
            WAITING_END: [MessageHandler(Filters.text & ~Filters.command, waiting_end)],
            WAITING_INTERVAL: [MessageHandler(Filters.text & ~Filters.command, waiting_interval)],
            CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, confirmation)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="task_conversation",
        persistent=False,
    )

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler("listtasks", listtasks))
    dispatcher.add_handler(CommandHandler("deletetask", deletetask))
    dispatcher.add_handler(CommandHandler("cancel", cancel))

    if IS_RENDER and WEBHOOK_URL:
        # Render 部署，使用Webhook
        webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
        bot.set_webhook(webhook_url)
        logger.info(f"Webhook已设置: {webhook_url}")
        app.run(host="0.0.0.0", port=PORT)
    else:
        # 本地调试，长轮询
        updater.start_polling()
        updater.idle()