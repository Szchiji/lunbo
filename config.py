import os
import json

# Telegram 机器人 Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Webhook 地址（可选）
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 数据库连接串
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://user:password@localhost:5432/dbname"  # 默认值请自行替换
)

# 群组配置
GROUPS_JSON = os.getenv("GROUPS", '{"-1002764616804":"群名"}')

try:
    GROUPS_TMP = json.loads(GROUPS_JSON)
except Exception as e:
    print(f"GROUPS 环境变量格式错误: {e}")
    GROUPS_TMP = {}

GROUPS = {}
for k, v in GROUPS_TMP.items():
    try:
        GROUPS[int(k)] = v
    except Exception:
        try:
            GROUPS[int(str(k).replace('"', ''))] = v
        except Exception:
            pass

# 其他自定义配置可继续添加
