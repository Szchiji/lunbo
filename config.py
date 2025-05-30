import os

BOT_TOKEN = os.getenv("BOT_TOKEN")  # 设置为环境变量
WEBHOOK_HOST = "https://lunbo.onrender.com"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"