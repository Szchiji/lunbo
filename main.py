# main.py
from fastapi import FastAPI, Request, Response
from aiogram import types
from aiogram.types import Update
from app.bot import bot, dp
import app.handlers  # 确保这里有处理逻辑的 handlers 模块
from app.config import WEBHOOK_PATH, WEBHOOK_URL
from app.database import init_db
from app.scheduler import scheduler

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    # 初始化数据库
    init_db()
    # 删除之前的 webhook，防止冲突
    await bot.delete_webhook()
    # 设置新的 webhook 地址
    await bot.set_webhook(WEBHOOK_URL)
    # 启动调度器
    scheduler.start()
    print(f"Webhook 已设置为: {WEBHOOK_URL}，调度器启动")

@app.on_event("shutdown")
async def on_shutdown():
    # 关闭 bot 会话，释放资源
    await bot.session.close()
    print("Bot session 已关闭")

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    # 解析 Telegram 发送来的更新数据
    data = await request.json()
    update = Update(**data)
    # 把更新交给 Dispatcher 处理
    await dp.process_update(update)
    # 回复 200 OK 表示收到
    return Response(status_code=200)