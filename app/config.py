import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "你的bot_token")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://your.domain")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

DATABASE_PATH = "app/tasks.db"