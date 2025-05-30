import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "your-bot-token")
DOMAIN = os.getenv("DOMAIN", "https://lunbo.onrender.com")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = DOMAIN + WEBHOOK_PATH

DATABASE_PATH = os.getenv("DATABASE_PATH", "/tmp/db.sqlite3")