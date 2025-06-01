import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from handlers import register_handlers
from config import TOKEN, PORT, WEBHOOK_URL, IS_RENDER
from scheduler import start_scheduler
from database import init_db

app = Flask(__name__)
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, update_queue=None, use_context=True)
register_handlers(dispatcher)

@app.route("/")
def index():
    return "🤖 Bot Running"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

if __name__ == "__main__":
    init_db()
    start_scheduler()
    if IS_RENDER and WEBHOOK_URL:
        bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    app.run(host="0.0.0.0", port=PORT)