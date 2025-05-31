import os
import json
import time
import schedule
import pytz
from uuid import uuid4
from threading import Thread
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 配置
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
IS_RENDER = os.getenv('RENDER', '').lower() == 'true'
DATA_FILE = '/tmp/scheduled_messages.json' if IS_RENDER else 'scheduled_messages.json'

# 修复 PORT 环境变量为空时报错
raw_port = os.getenv('PORT')
PORT = int(raw_port) if raw_port and raw_port.isdigit() else 10000

# 消息类型
class MessageType:
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"

class ButtonType:
    URL = "url"
    CALLBACK = "callback"

bot = Bot(token=TOKEN)
dispatcher = None

# 数据持久化
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

        if message_data['message_type'] == MessageType.PHOTO:
            with open(message_data['file_path'], 'rb') as photo:
                bot.send_photo(chat_id=chat_id, photo=photo, caption=message_data['content'], reply_markup=reply_markup)
        elif message_data['message_type'] == MessageType.VIDEO:
            with open(message_data['file_path'], 'rb') as video:
                bot.send_video(chat_id=chat_id, video=video, caption=message_data['content'], reply_markup=reply_markup)
        else:
            bot.send_message(chat_id=chat_id, text=message_data['content'], reply_markup=reply_markup)
        return True
    except Exception as e:
        print(f"发送失败: {e}")
        return False

# 定时任务系统
def check_due_messages():
    now = datetime.now(pytz.utc)
    for msg in scheduled_messages:
        if msg.get('active', True):
            try:
                start = datetime.strptime(msg['start_time'], '%Y-%m-%d %H:%M').replace(tzinfo=pytz.utc)
                end = datetime.strptime(msg['end_time'], '%Y-%m-%d %H:%M').replace(tzinfo=pytz.utc)
                if start <= now <= end:
                    hours_since_start = (now - start).total_seconds() / 3600
                    if hours_since_start % 3 == 0:
                        send_rich_message(msg['chat_id'], msg)
            except Exception as e:
                print(f"检查失败: {e}")

def schedule_worker():
    print("⏰ 定时任务系统启动")
    while True:
        schedule.run_pending()
        time.sleep(1)

def init_scheduler():
    if not IS_RENDER:
        schedule.clear()
        for msg in scheduled_messages:
            if msg.get('active', True):
                try:
                    start = datetime.strptime(msg['start_time'], '%Y-%m-%d %H:%M')
                    end = datetime.strptime(msg['end_time'], '%Y-%m-%d %H:%M')
                    current = start
                    while current <= end:
                        def make_job(m, t):
                            def job(): send_rich_message(m['chat_id'], m)
                            return job
                        schedule.every().day.at(current.strftime('%H:%M')).do(make_job(msg, current))
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

# 指令处理
def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("📚 使用 /addschedule、/listschedule、/deleteschedule、/editschedule 来管理定时消息")

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

def list_schedule(update: Update, context: CallbackContext):
    if not scheduled_messages:
        update.message.reply_text("暂无定时任务")
        return
    response = [f"{m['id']}: {m['start_time']} - {m['end_time']} 内容: {m['content'][:30]}" for m in scheduled_messages]
    update.message.reply_text('\n'.join(response))

def delete_schedule(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("请提供 ID")
        return
    msg_id = context.args[0]
    global scheduled_messages
    before = len(scheduled_messages)
    scheduled_messages = [m for m in scheduled_messages if m['id'] != msg_id]
    save_messages(scheduled_messages)
    if len(scheduled_messages) < before:
        update.message.reply_text("✅ 删除成功")
    else:
        update.message.reply_text("❌ 未找到该消息")

def edit_schedule(update: Update, context: CallbackContext):
    try:
        args = context.args
        if len(args) < 2:
            update.message.reply_text("用法: /editschedule <消息ID> <字段>=<新值> ...")
            return
        msg_id = args[0]
        updates = args[1:]
        msg = next((m for m in scheduled_messages if m['id'] == msg_id), None)
        if not msg:
            update.message.reply_text("未找到指定的消息")
            return
        for item in updates:
            if '=' in item:
                key, value = item.split('=', 1)
                if key in msg:
                    msg[key] = value
        save_messages(scheduled_messages)
        update.message.reply_text(f"✅ 消息 {msg_id} 已更新")
    except Exception as e:
        update.message.reply_text(f"❌ 错误: {e}")

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
    dispatcher.add_handler(CommandHandler("editschedule", edit_schedule))
    init_scheduler()
    if IS_RENDER and os.getenv('WEBHOOK_URL'):
        updater.bot.set_webhook(os.getenv('WEBHOOK_URL'))
    if IS_RENDER:
        Thread(target=run_flask).start()
        updater.start_polling()
    else:
        run_flask()

if __name__ == '__main__':
    main()