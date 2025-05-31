import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
import schedule
import time
from threading import Thread
from datetime import datetime, timedelta
import pytz
import json
from dotenv import load_dotenv
from uuid import uuid4

# 初始化环境
load_dotenv()
app = Flask(__name__)

# 配置
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
PORT = int(os.getenv('PORT', 10000))
DATA_FILE = '/tmp/scheduled_messages.json' if os.getenv('RENDER') else 'scheduled_messages.json'
IS_RENDER = os.getenv('RENDER', '').lower() == 'true'

# 消息类型
class MessageType:
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"

class ButtonType:
    URL = "url"
    CALLBACK = "callback"

# 初始化机器人
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

# 消息发送
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
            content = message_data['content']
            if message_data.get('file_path'):
                with open(message_data['file_path'], 'rb') as photo:
                    return bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=content,
                        reply_markup=reply_markup
                    )
            else:
                return bot.send_photo(
                    chat_id=chat_id,
                    photo=content,
                    caption=content if content else None,
                    reply_markup=reply_markup
                )
        elif message_data['message_type'] == MessageType.VIDEO:
            # 类似图片处理
            pass
        else:
            return bot.send_message(
                chat_id=chat_id,
                text=message_data['content'],
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"发送失败: {e}")
        return False

# 定时任务系统
def check_due_messages():
    now = datetime.now(pytz.utc)
    for msg in scheduled_messages:
        if msg.get('active', True):
            start = datetime.strptime(msg['start_time'], '%Y-%m-%d %H:%M').replace(tzinfo=pytz.utc)
            end = datetime.strptime(msg['end_time'], '%Y-%m-%d %H:%M').replace(tzinfo=pytz.utc)
            
            if start <= now <= end:
                hours_since_start = (now - start).total_seconds() / 3600
                if hours_since_start % 3 == 0:
                    send_rich_message(msg['chat_id'], msg)

def schedule_worker():
    while True:
        schedule.run_pending()
        time.sleep(1)

def init_scheduler():
    if not IS_RENDER:
        schedule.clear()
        for msg in scheduled_messages:
            if msg.get('active', True):
                start = datetime.strptime(msg['start_time'], '%Y-%m-%d %H:%M')
                current = start
                while current <= datetime.strptime(msg['end_time'], '%Y-%m-%d %H:%M'):
                    schedule.every().day.at(current.strftime('%H:%M')).do(
                        lambda: send_rich_message(msg['chat_id'], msg)
                    current += timedelta(hours=3)
        Thread(target=schedule_worker, daemon=True).start()

# Web 路由
@app.route('/')
def home():
    if IS_RENDER:
        check_due_messages()
    return "🤖 机器人运行中 | /help 查看指令"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    if dispatcher:
        dispatcher.process_update(update)
    return 'OK'

@app.route('/ping')
def ping():
    check_due_messages()
    return "PONG"

# 指令处理
def help_command(update: Update, context: CallbackContext):
    help_text = """
📚 定时消息系统使用指南:

1. 添加纯文本定时消息(可带按钮):
/addschedule <开始日期> <开始时间> <结束日期> <结束时间> <消息内容>
例: /addschedule 2023-12-01 09:00 2023-12-31 18:00 每日提醒

2. 添加媒体消息(图片/视频):
先发送媒体文件到聊天，然后回复该消息:
/addschedule <开始日期> <开始时间> <结束日期> <结束时间>

3. 添加按钮:
/addbutton <消息ID> <url/callback> <按钮文本> <链接或回调数据>
示例:
/addbutton abc123 url 访问官网 https://example.com
/addbutton abc123 callback 确认 received_confirm

其他命令:
/listschedule - 查看所有定时任务
/deleteschedule <ID> - 删除任务
"""
    update.message.reply_text(help_text)

def add_schedule(update: Update, context: CallbackContext):
    try:
        reply_to = update.message.reply_to_message
        msg_type = MessageType.TEXT
        content = ""
        file_path = ""
        
        if reply_to:
            if reply_to.photo:
                msg_type = MessageType.PHOTO
                file_id = reply_to.photo[-1].file_id
                content = file_id
            elif reply_to.video:
                msg_type = MessageType.VIDEO
                file_id = reply_to.video.file_id
                content = file_id
            content = reply_to.caption if reply_to.caption else content
        
        args = context.args
        if msg_type == MessageType.TEXT:
            if len(args) < 5:
                raise ValueError("参数不足")
            start_date, start_time, end_date, end_time = args[:4]
            content = ' '.join(args[4:])
        else:
            if len(args) < 4:
                raise ValueError("参数不足")
            start_date, start_time, end_date, end_time = args[:4]
        
        new_msg = create_message_template()
        new_msg.update({
            'chat_id': update.message.chat_id,
            'start_time': f"{start_date} {start_time}",
            'end_time': f"{end_date} {end_time}",
            'message_type': msg_type,
            'content': content,
            'file_path': file_path
        })
        
        scheduled_messages.append(new_msg)
        save_messages(scheduled_messages)
        init_scheduler()
        
        update.message.reply_text(f"✅ 定时消息已添加 (ID: {new_msg['id']})")
        
    except Exception as e:
        update.message.reply_text(f"❌ 错误: {str(e)}")

# 其他命令处理函数（listschedule, addbutton, deleteschedule等）
# 因篇幅限制，请参考前文实现

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def main():
    global dispatcher
    
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # 注册指令
    dispatcher.add_handler(CommandHandler("start", help_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("addschedule", add_schedule))
    # 添加其他指令...
    
    init_scheduler()
    
    if IS_RENDER and os.getenv('WEBHOOK_URL'):
        updater.bot.set_webhook(os.getenv('WEBHOOK_URL'))
    
    if IS_RENDER:
        Thread(target=run_flask).start()
        updater.start_polling()
    else:
        app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()