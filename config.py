import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GROUP_IDS = [int(i) for i in os.getenv("GROUP_IDS", "-1001234567890").split(",")]
POSTGRES_DSN = os.getenv("POSTGRES_DSN")
