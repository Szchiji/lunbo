from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from app.config import config
from app.handlers import router
from app.scheduler import scheduler

# 创建 Bot 和 Dispatcher 实例
bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
dp.include_router(router)

# FastAPI 实例（Render 会寻找这个变量）
app = FastAPI()


@app.on_event("startup")
async def on_startup():
    # 清除旧 webhook 并设置新的
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(f"{config.DOMAIN}/webhook")
    scheduler.start()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)  # Aiogram 3 正确的处理更新方式
    return {"ok": True}