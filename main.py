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
                    bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=content,
                        reply_markup=reply_markup
                    )
            else:
                bot.send_photo(
                    chat_id=chat_id,
                    photo=content,
                    caption=content if content else None,
                    reply_markup=reply_markup
                )
            return True
        elif message_data['message_type'] == MessageType.VIDEO:
            # 类似图片处理
            pass
        else:
            bot.send_message(
                chat_id=chat_id,
                text=message_data['content'],
                reply_markup=reply_markup
            )
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
                print(f"检查消息失败: {e}")

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
                        # 使用闭包捕获当前值
                        def make_send_job(message, send_time):
                            def job():
                                print(f"定时发送消息: {send_time}")
                                send_rich_message(message['chat_id'], message)
                            return job
                        
                        schedule.every().day.at(current.strftime('%H:%M')).do(
                            make_send_job(msg, current)
                        )
                        current += timedelta(hours=3)
                except Exception as e:
                    print(f"初始化定时任务失败: {e}")
        
        Thread(target=schedule_worker, daemon=True).start()

# Web 路由
@app.route('/')
def home():
    if IS_RENDER:
        check_due_messages()
    return "🤖 机器人运行中 | /help 查看指令"

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
        if not args or len(args) < 4:
            raise ValueError("参数不足，格式: /addschedule 开始日期 开始时间 结束日期 结束时间 [消息]")
        
        start_date, start_time, end_date, end_time = args[:4]
        
        if msg_type == MessageType.TEXT and len(args) >= 5:
            content = ' '.join(args[4:])
        
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

def list_schedule(update: Update, context: CallbackContext):
    if not scheduled_messages:
        update.message.reply_text("ℹ️ 没有定时消息")
        return
        
    response = ["📅 定时消息列表:"]
    for msg in scheduled_messages:
        status = "✅ 活跃" if msg.get('active', True) else "❌ 停用"
        response.append(
            f"ID: {msg['id']}\n"
            f"时间: {msg['start_time']} 至 {msg['end_time']}\n"
            f"状态: {status}\n"
            f"类型: {msg['message_type']}\n"
            f"内容: {msg['content'][:50]}{'...' if len(msg['content']) > 50 else ''}\n"
        )
    
    update.message.reply_text('\n'.join(response))

def delete_schedule(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ 需要提供消息ID")
        return
        
    msg_id = context.args[0]
    global scheduled_messages
    initial_count = len(scheduled_messages)
    
    # 过滤掉要删除的消息
    scheduled_messages = [msg for msg in scheduled_messages if msg['id'] != msg_id]
    
    if len(scheduled_messages) < initial_count:
        save_messages(scheduled_messages)
        init_scheduler()
        update.message.reply_text(f"✅ 消息 {msg_id} 已删除")
    else:
        update.message.reply_text("❌ 未找到该ID的消息")

def add_button(update: Update, context: CallbackContext):
    try:
        if not context.args or len(context.args) < 4:
            update.message.reply_text("❌ 格式: /addbutton <消息ID> <url/callback> <按钮文本> <链接或回调数据>")
            return
        
        msg_id, btn_type, btn_text = context.args[:3]
        btn_data = ' '.join(context.args[3:])
        
        # 验证按钮类型
        if btn_type not in [ButtonType.URL, ButtonType.CALLBACK]:
            raise ValueError("按钮类型必须是 'url' 或 'callback'")
        
        # 查找消息
        for msg in scheduled_messages:
            if msg['id'] == msg_id:
                msg['buttons'].append({
                    'type': btn_type,
                    'text': btn_text,
                    'data': btn_data
                })
                save_messages(scheduled_messages)
                update.message.reply_text(f"✅ 按钮已添加到消息 {msg_id}")
                return
        
        update.message.reply_text("❌ 未找到该ID的消息")
        
    except Exception as e:
        update.message.reply_text(f"❌ 错误: {str(e)}")

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
    dispatcher.add_handler(CommandHandler("addbutton", add_button))
    dispatcher.add_handler(CommandHandler("listschedule", list_schedule))
    dispatcher.add_handler(CommandHandler("deleteschedule", delete_schedule))
    
    # 初始化定时任务
    init_scheduler()
    
    # 设置Webhook（如果配置了）
    if IS_RENDER and os.getenv('WEBHOOK_URL'):
        updater.bot.set_webhook(os.getenv('WEBHOOK_URL'))
        print(f"Webhook 设置为: {os.getenv('WEBHOOK_URL')}")
    
    # 启动方式取决于环境
    if IS_RENDER:
        print("🚀 在 Render 环境中启动")
        Thread(target=run_flask).start()
        updater.start_polling()
    else:
        print("💻 在本地环境中启动")
        app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()