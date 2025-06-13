import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 支持群名映射：GROUPS=-1001234567890:群1,-1009876543210:群2
GROUPS = dict(
    i.split(":") for i in os.getenv("GROUPS", "-1001234567890:测试群").split(",")
)
# 群ID强制转为int
GROUPS = {int(k): v for k, v in GROUPS.items()}

POSTGRES_DSN = os.getenv("POSTGRES_DSN")
