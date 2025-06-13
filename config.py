import os
import json

# Telegram 机器人 Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 管理员ID列表（环境变量 ADMINS，要求是 JSON 数组，例如: [123456789, 987654321]）
ADMINS_JSON = os.getenv("ADMINS", "[]")  # 默认空列表
try:
    ADMINS = json.loads(ADMINS_JSON)
    if not isinstance(ADMINS, list) and not isinstance(ADMINS, set):
        ADMINS = [ADMINS]  # 兼容 ADMINS 直接是一个数字的情况
except Exception as e:
    print(f"ADMINS 环境变量格式错误: {e}")
    ADMINS = []

# Webhook 地址（可选）
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 数据库连接串
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://user:password@localhost:5432/dbname"  # 默认值请自行替换
)

# 群组配置（环境变量 GROUPS，要求是 JSON 字典，例如: {"-1001234567890": "群A", "-1002345678901": "群B"}）
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
