from flask import Flask, request
import telebot
from config import BOT_TOKEN, WEBHOOK_URL
from handlers import create_task, edit_task, delete_task
from scheduler import scheduler
from models import init_db

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

# 初始化数据库
init_db()

# 注册处理器
create_task.register_handlers(bot)
edit_task.register_handlers(bot)
delete_task.register_handlers(bot)

# 设置 Webhook
@app.route('/telegram', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'OK', 200

# 启动 Webhook
@app.before_first_request
def setup_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + '/telegram')

# 启动调度器
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)