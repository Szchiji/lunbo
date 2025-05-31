import os
from flask import Flask, request
from telegram import (
    Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
)
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, CallbackContext, ConversationHandler, MessageHandler, Filters
)
import schedule
import time
from threading import Thread
from datetime import datetime, timedelta
import pytz
import json
from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()

app = Flask(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
IS_RENDER = os.getenv('RENDER', '').lower() == 'true'
DATA_FILE = '/tmp/scheduled_messages.json' if IS_RENDER else 'scheduled_messages.json'

raw_port = os.getenv('PORT')
PORT = int(raw_port) if raw_port and raw_port.isdigit() else 10000

class MessageType:
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"

class ButtonType:
    URL = "url"
    CALLBACK = "callback"

bot = Bot(token=TOKEN)
dispatcher = None

# FSM States for edit flow
EDIT_TEXT, EDIT_MEDIA, EDIT_START_TIME, EDIT_END_TIME, CONFIRM_EDIT = range(5)

def load_messages():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_messages(messages):
    with open(DATA_FILE, 'w') as f:
        json.dump(messages, f)

scheduled_messages = load_messages()

def create_message_template():
    return {
        'id': str(uuid4()),
        'chat_id': "",
        'start_time': "",
        'end_time': "",
        'message_type': MessageType.TEXT,
        'content': "",
        'file_path': "",
        'buttons': [],
        'active': True,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

def send_rich_message(chat_id, message_data):
    try:
        buttons = []
        for btn in message_data.get('buttons', []):
            if btn['type'] == ButtonType.URL:
                buttons.append(InlineKeyboardButton(btn['text'], url=btn['data']))
            else:
                buttons.append(InlineKeyboardButton(btn['text'], callback_data=btn['data']))
        reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

        if message_data['message_type'] == MessageType.PHOTO and message_data.get('file_path'):
            with open(message_data['file_path'], 'rb') as photo:
                bot.send_photo(chat_id=chat_id, photo=photo, caption=message_data['content'], reply_markup=reply_markup)
        elif message_data['message_type'] == MessageType.VIDEO and message_data.get('file_path'):
            with open(message_data['file_path'], 'rb') as video:
                bot.send_video(chat_id=chat_id, video=video, caption=message_data['content'], reply_markup=reply_markup)
        else:
            bot.send_message(chat_id=chat_id, text=message_data['content'], reply_markup=reply_markup)
        return True
    except Exception as e:
        print(f"发送失败: {e}")
        return False

def check_due_messages():
    now = datetime.now(pytz.utc)
    for msg in scheduled_messages:
        if msg.get('active', True):
            try:
                start = datetime.strptime(msg['start_time'], '%Y-%m-%d %H:%M').replace(tzinfo=pytz.utc)
                end = datetime.strptime(msg['end_time'], '%Y-%m-%d %H:%M').replace(tzinfo=pytz.utc)
                if start <= now <= end:
                    hours_since_start = (now - start).total_seconds() / 3600
                    # 这里简单判断每3小时发送一次
                    if int(hours_since_start) % 3 == 0:
                        send_rich_message(msg['chat_id'], msg)
            except Exception as e:
                print(f"检查失败: {e}")

def schedule_worker():
    print("⏰ 定时任务系统启动")
    while True:
        schedule.run_pending()
        time.sleep(1)

def init_scheduler():
    schedule.clear()
    for msg in scheduled_messages:
        if msg.get('active', True):
            try:
                start = datetime.strptime(msg['start_time'], '%Y-%m-%d %H:%M')
                end = datetime.strptime(msg['end_time'], '%Y-%m-%d %H:%M')
                current = start
                while current <= end:
                    def make_job(m=msg):
                        def job(): send_rich_message(m['chat_id'], m)
                        return job
                    schedule.every().day.at(current.strftime('%H:%M')).do(make_job())
                    current += timedelta(hours=3)
            except Exception as e:
                print(f"调度失败: {e}")
    Thread(target=schedule_worker, daemon=True).start()

@app.route('/')
def home():
    if IS_RENDER:
        check_due_messages()
    return "🤖 机器人运行中"

@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_json()
    update = Update.de_json(json_data, bot)
    if dispatcher:
        dispatcher.process_update(update)
    return 'OK'

@app.route('/ping')
def ping():
    check_due_messages()
    return "PONG"

# --- Bot Handlers ---

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("📚 使用 /addschedule、/listschedule、/deleteschedule 来管理定时消息")

def add_schedule(update: Update, context: CallbackContext):
    try:
        args = context.args
        if len(args) < 4:
            update.message.reply_text("用法: /addschedule <开始日期> <开始时间> <结束日期> <结束时间> <消息内容>")
            return
        start_date, start_time, end_date, end_time = args[:4]
        content = ' '.join(args[4:]) if len(args) > 4 else '定时消息'
        new_msg = create_message_template()
        new_msg.update({
            'chat_id': update.message.chat_id,
            'start_time': f"{start_date} {start_time}",
            'end_time': f"{end_date} {end_time}",
            'message_type': MessageType.TEXT,
            'content': content
        })
        scheduled_messages.append(new_msg)
        save_messages(scheduled_messages)
        init_scheduler()
        update.message.reply_text(f"✅ 已添加消息 (ID: {new_msg['id']})")
    except Exception as e:
        update.message.reply_text(f"❌ 错误: {e}")

# 查看任务，附带修改/删除按钮
def list_schedule(update: Update, context: CallbackContext):
    if not scheduled_messages:
        update.message.reply_text("暂无定时任务")
        return

    for msg in scheduled_messages:
        text = (f"ID: {msg['id']}\n"
                f"时间: {msg['start_time']} - {msg['end_time']}\n"
                f"内容: {msg['content'][:100]}")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📝 修改", callback_data=f"edit:{msg['id']}"),
            InlineKeyboardButton("🗑 删除", callback_data=f"delete:{msg['id']}")
        ]])
        update.message.reply_text(text, reply_markup=keyboard)

# 删除按钮回调
def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("delete:"):
        msg_id = data.split("delete:")[1]
        global scheduled_messages
        before = len(scheduled_messages)
        scheduled_messages = [m for m in scheduled_messages if m['id'] != msg_id]
        save_messages(scheduled_messages)
        init_scheduler()
        if len(scheduled_messages) < before:
            query.edit_message_text("✅ 删除成功")
        else:
            query.edit_message_text("❌ 未找到该消息")

    elif data.startswith("edit:"):
        msg_id = data.split("edit:")[1]
        # 找到消息
        msg = next((m for m in scheduled_messages if m['id'] == msg_id), None)
        if not msg:
            query.edit_message_text("❌ 未找到该消息")
            return ConversationHandler.END

        context.user_data['edit_msg'] = msg
        query.edit_message_text(f"✏️ 开始修改消息内容，请发送新的文字内容（当前内容：{msg['content'][:100]}）")
        return EDIT_TEXT

# 编辑消息流程 - 文字输入
def edit_text(update: Update, context: CallbackContext):
    new_text = update.message.text
    msg = context.user_data['edit_msg']
    msg['content'] = new_text
    save_messages(scheduled_messages)
    update.message.reply_text("✅ 文字内容已更新。你可以发送新的媒体文件（照片或视频）来替换，或发送 /skip 跳过媒体修改。")
    return EDIT_MEDIA

# 编辑消息流程 - 接收媒体
def edit_media(update: Update, context: CallbackContext):
    msg = context.user_data['edit_msg']
    file_id = None
    file_path = None
    # 处理照片
    if update.message.photo:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        msg['message_type'] = MessageType.PHOTO
    elif update.message.video:
        video = update.message.video
        file_id = video.file_id
        msg['message_type'] = MessageType.VIDEO
    else:
        update.message.reply_text("请发送照片或视频，或发送 /skip 跳过。")
        return EDIT_MEDIA

    # 下载文件保存到本地
    new_file = bot.get_file(file_id)
    file_path = f"media/{msg['id']}"
    if msg['message_type'] == MessageType.PHOTO:
        file_path += ".jpg"
    else:
        file_path += ".mp4"
    os.makedirs("media", exist_ok=True)
    new_file.download(custom_path=file_path)
    msg['file_path'] = file_path
    save_messages(scheduled_messages)

    update.message.reply_text("✅ 媒体文件已更新。\n请输入新的开始时间，格式：YYYY-MM-DD HH:MM")
    return EDIT_START_TIME

def skip_media(update: Update, context: CallbackContext):
    update.message.reply_text("已跳过媒体修改。\n请输入新的开始时间，格式：YYYY-MM-DD HH:MM")
    return EDIT_START_TIME

def edit_start_time(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, '%Y-%m-%d %H:%M')
    except Exception:
        update.message.reply_text("格式错误，请输入正确格式：YYYY-MM-DD HH:MM")
        return EDIT_START_TIME
    context.user_data['edit_msg']['start_time'] = text
    update.message.reply_text("请输入新的结束时间，格式：YYYY-MM-DD HH:MM")
    return EDIT_END_TIME

def edit_end_time(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, '%Y-%m-%d %H:%M')
    except Exception:
        update.message.reply_text("格式错误，请输入正确格式：YYYY-MM-DD HH:MM")
        return EDIT_END_TIME
    context.user_data['edit_msg']['end_time'] = text
    save_messages(scheduled_messages)
    update.message.reply_text("✅ 修改完成。")
    init_scheduler()
    return ConversationHandler.END

def cancel_edit(update: Update, context: CallbackContext):
    update.message.reply_text("❌ 修改已取消。")
    return ConversationHandler.END

# 删除任务命令
def delete_schedule(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("请提供任务ID")
        return
    msg_id = context.args[0]
    global scheduled_messages
    before = len(scheduled_messages)
    scheduled_messages = [m for m in scheduled_messages if m['id'] != msg_id]
    save_messages(scheduled_messages)
    init_scheduler()
    if len(scheduled_messages) < before:
        update.message.reply_text("✅ 删除成功")
    else:
        update.message.reply_text("❌ 未找到该消息")

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def main():
    global dispatcher
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", help_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("addschedule", add_schedule))
    dispatcher.add_handler(CommandHandler("listschedule", list_schedule))
    dispatcher.add_handler(CommandHandler("deleteschedule", delete_schedule))
    dispatcher.add_handler(CallbackQueryHandler(button_callback))

    # 编辑对话管理器
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern='^edit:')],
        states={
            EDIT_TEXT: [MessageHandler(Filters.text & ~Filters.command, edit_text)],
            EDIT_MEDIA: [
                MessageHandler(Filters.photo | Filters.video, edit_media),
                CommandHandler('skip', skip_media)
            ],
            EDIT_START_TIME: [MessageHandler(Filters.text & ~Filters.command, edit_start_time)],
            EDIT_END_TIME: [MessageHandler(Filters.text & ~Filters.command, edit_end_time)]
        },
        fallbacks=[CommandHandler('cancel', cancel_edit)],
        allow_reentry=True
    )
    dispatcher.add_handler(conv_handler)

    init_scheduler()

    if IS_RENDER and os.getenv('WEBHOOK_URL'):
        updater.bot.set_webhook(os.getenv('WEBHOOK_URL'))

    if IS_RENDER:
        Thread(target=run_flask, daemon=True).start()
        updater.start_polling()
        updater.idle()
    else:
        run_flask()

if __name__ == '__main__':
    main()