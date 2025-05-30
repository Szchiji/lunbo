import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "your-telegram-bot-token")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://your-render-app.onrender.com{WEBHOOK_PATH}"