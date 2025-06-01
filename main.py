import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, ConversationHandler
from db import init_db
from handlers import (
    start_add, add_text, add_media_type, add_media, add_buttons,
    add_interval, add_start, add_end, add_confirm, cancel,
    list_tasks, delete_task
)
import logging

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # 例如 https://yourdomain.com/telegram

app = Flask(__name__)
bot = Bot(token=TOKEN)

# 初始化数据库
init_db()

# Dispatcher 用于路由处理
from telegram.ext import CallbackContext

dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# 添加任务的对话流程
add_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('add_task', start_add)],
    states={
        0: [MessageHandler(Filters.text & ~Filters.command, add_text)],
        1: [MessageHandler(Filters.text & ~Filters.command, add_media_type)],
        2: [MessageHandler(Filters.photo | Filters.video, add_media)],
        3: [MessageHandler(Filters.text & ~Filters.command, add_buttons)],
        4: [MessageHandler(Filters.text & ~Filters.command, add_interval)],
        5: [MessageHandler(Filters.text & ~Filters.command, add_start)],
        6: [MessageHandler(Filters.text & ~Filters.command, add_end)],
        7: [MessageHandler(Filters.text & ~Filters.command, add_confirm)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

dispatcher.add_handler(add_conv_handler)
dispatcher.add_handler(CommandHandler('list_tasks', list_tasks))
dispatcher.add_handler(CommandHandler('delete_task', delete_task))

@app.route('/telegram', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    # 设置Webhook地址，启动时自动调用
    bot.set_webhook(WEBHOOK_URL + "/telegram")
    logging.info(f"Webhook set to {WEBHOOK_URL}/telegram")
    app.run(host="0.0.0.0", port=port)