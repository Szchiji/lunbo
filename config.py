import os
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GROUPS_JSON = os.getenv("GROUPS", '{"-1002764616804":"群名"}')
GROUPS_TMP = json.loads(GROUPS_JSON)
GROUPS = {}
for k, v in GROUPS_TMP.items():
    try:
        GROUPS[int(k)] = v
    except Exception:
        try:
            GROUPS[int(str(k).replace('"', ''))] = v
        except Exception:
            pass
