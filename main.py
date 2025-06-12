import os
import logging
from telegram.ext import ApplicationBuilder

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST")  # 你的 Render 域名或自定义域名
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 10000))  # Render 会自动分配端口

from plugins.main_menu import show_main_menu  # ...省略其它引入...

async def start(update, context):
    await update.message.reply_text("欢迎使用！")
    await show_main_menu(update, context)

app = ApplicationBuilder()\
    .token(TOKEN)\
    .webhook_url(WEBHOOK_URL)\
    .build()

# ...添加你的各种handler...

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
    ))
