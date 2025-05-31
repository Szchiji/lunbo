from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from flask import Flask, request
import schedule
import time
from threading import Thread
from datetime import datetime, timedelta
import pytz
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 配置信息
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
IS_RENDER = os.getenv('RENDER', '').lower() == 'true'
PORT = int(os.getenv('PORT', 10000))  # Render 提供动态端口
DATA_FILE = 'scheduled_messages.json'

# 初始化机器人
bot = Bot(token=TOKEN)
dispatcher = None

# 加载/保存消息数据
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

# 发送消息函数
def send_message(chat_id, text):
    try:
        bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        print(f"发送消息失败: {e}")
        return False

# 检查并发送到期消息 (Render 适配)
def check_and_send_due_messages():
    now = datetime.now(pytz.utc)
    for msg in scheduled_messages:
        if msg.get('active', True):
            start_time = datetime.strptime(msg['start_time'], '%Y-%m-%d %H:%M').replace(tzinfo=pytz.utc)
            end_time = datetime.strptime(msg['end_time'], '%Y-%m-%d %H:%M').replace(tzinfo=pytz.utc)
            
            if start_time <= now <= end_time:
                # 检查是否是3小时的倍数
                hours_since_start = (now - start_time).total_seconds() / 3600
                if hours_since_start % 3 == 0:
                    send_message(msg['chat_id'], msg['message'])

# 启动调度器
def start_scheduler():
    if not IS_RENDER:
        schedule.clear()
        for msg in scheduled_messages:
            if msg.get('active', True):
                start_time = datetime.strptime(msg['start_time'], '%Y-%m-%d %H:%M')
                end_time = datetime.strptime(msg['end_time'], '%Y-%m-%d %H:%M')
                
                current_time = start_time
                while current_time <= end_time:
                    schedule.every().day.at(current_time.strftime('%H:%M')).do(
                        send_message, msg['chat_id'], msg['message']
                    ).tag(msg['id'])
                    current_time += timedelta(hours=3)
        
        Thread(target=schedule_worker, daemon=True).start()

def schedule_worker():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Webhook 路由
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/')
def home():
    if IS_RENDER:
        check_and_send_due_messages()
    return 'Telegram Schedule Bot is running!'

# 添加你的命令处理器 (同前)
# ...

def main():
    global dispatcher
    
    # 设置Webhook
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # 添加命令处理器
    dispatcher.add_handler(CommandHandler("start", help_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("addschedule", add_schedule))
    dispatcher.add_handler(CommandHandler("listschedule", list_schedule))
    dispatcher.add_handler(CommandHandler("deleteschedule", delete_schedule))
    dispatcher.add_handler(CommandHandler("activateschedule", 
        lambda u, c: toggle_schedule(u, c, True)))
    dispatcher.add_handler(CommandHandler("deactivateschedule", 
        lambda u, c: toggle_schedule(u, c, False)))
    
    # 在 Render 上不需要设置 Webhook URL
    if not IS_RENDER:
        WEBHOOK_URL = os.getenv('WEBHOOK_URL')
        CERT_PATH = os.getenv('CERT_PATH')
        if WEBHOOK_URL and CERT_PATH:
            updater.bot.setWebhook(
                WEBHOOK_URL,
                certificate=open(CERT_PATH, 'rb'),
                max_connections=40
            )
    
    # 启动调度器
    start_scheduler()
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()
