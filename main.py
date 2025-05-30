from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Update
from aiogram.dispatcher.webhook import configure_app
from app import config
import asyncio

bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

app = FastAPI()

# 把 aiogram Dispatcher 绑定到 FastAPI 路由上
@app.post(config.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    await dp.process_update(update)
    return {"ok": True}

# 启动时设置 webhook
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(config.WEBHOOK_URL)

# 关闭时删除 webhook
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()

# 示例简单命令处理器
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("Hello! Bot started.")

# 运行这个脚本时使用 `uvicorn main:app --host 0.0.0.0 --port 10000`