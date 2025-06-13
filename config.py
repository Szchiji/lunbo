import os
from dotenv import load_dotenv

# 加载 .env 文件里的环境变量（如果有 .env 文件，推荐用 python-dotenv 管理敏感信息）
load_dotenv()

# Telegram 机器人 Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "your-telegram-bot-token")

# Webhook 地址（用于 Telegram 服务器推送消息到你的服务器）
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your.server.com/your-webhook-path")

# 支持的群组 ID 列表（可改为从环境变量读取或直接写死）
# 例如 [-1001234567890, -1009876543210]
GROUP_IDS = [
    int(gid) for gid in os.getenv("GROUP_IDS", "-1001234567890").split(",")
]

# Neon/PostgreSQL 数据库连接字符串
# 推荐在 .env 文件或环境变量里设置 POSTGRES_DSN
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://username:password@ep-xxx-xxx-xxx.us-east-2.aws.neon.tech/dbname"
)

# 可选：其它参数
# DEBUG = os.getenv("DEBUG", "0") == "1"
