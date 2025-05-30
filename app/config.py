import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "your-bot-token")
DOMAIN = os.getenv("DOMAIN", "https://your-app-name.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = DOMAIN + WEBHOOK_PATH

DATABASE_PATH = "data/database.db"