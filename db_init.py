import asyncio
from db import init_db

if __name__ == "__main__":
    asyncio.run(init_db())
    print("数据库表创建完成")
