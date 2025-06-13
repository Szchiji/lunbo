import asyncio
from db import init_db

asyncio.run(init_db())
print("数据库表创建完成")
