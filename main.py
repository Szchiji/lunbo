from fastapi import FastAPI, Request, Response
from aiogram import types
from aiogram.types import Update
from app.bot import bot, dp
import app.handlers
from app.config import WEBHOOK_PATH, WEBHOOK_URL
from app.database import init_db
from app.scheduler import scheduler
import asyncio

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    init_db()
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    scheduler.start()
    print("Webhook 设置成功，调度器启动")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    await dp.process_update(update)
    return Response(status_code=200)