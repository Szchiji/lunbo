# main.py

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage  # 3.x 正确导入路径
from aiogram.types import Update
import asyncio
import os

# 配置（也可以放到 config.py 导入）
BOT_TOKEN = os.getenv("BOT_TOKEN", "your-bot-token")
DOMAIN = os.getenv("DOMAIN", "https://your-app-name.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = DOMAIN + WEBHOOK_PATH

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage, bot=bot)

app = FastAPI()

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    await dp.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()

@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("Hello! Bot started.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)