import os
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from database import create_tables
from scheduler import scheduler, schedule_tasks
from handlers import add_task, list_tasks, delete_task, edit_task

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# 注册处理器
dp.include_routers(add_task.router, list_tasks.router, delete_task.router, edit_task.router)

@app.on_event("startup")
async def startup():
    create_tables()
    schedule_tasks(bot)
    scheduler.start()
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    await bot.set_webhook(webhook_url)
    print(f"✅ Webhook 设置为: {webhook_url}")

@app.post("/webhook")
async def telegram_webhook(req: Request):
    update = types.Update(**await req.json())
    await dp.feed_update(bot, update)
    return JSONResponse({"status": "ok"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
