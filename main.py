import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

BOT_TOKEN = os.getenv("BOT_TOKEN", "你的机器人TOKEN")
DOMAIN = os.getenv("DOMAIN", "https://你的域名")
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
    # 设置 webhook 地址
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    # 关闭时删除 webhook 和关闭会话
    await bot.delete_webhook()
    await bot.session.close()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("你好，机器人已启动！")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000)