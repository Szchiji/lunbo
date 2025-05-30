import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://lunbo.onrender.com/webhook")

# 初始化
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()
scheduler = AsyncIOScheduler()
scheduled_jobs = {}

# FastAPI Webhook Endpoint
@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return JSONResponse(content={"ok": True})

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    scheduler.start()
    print("✅ Webhook 已设置：", WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    scheduler.shutdown()

# 命令注册
@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("欢迎使用定时播报 Bot！\n\n使用 /add 添加定时任务，/list 查看，/delete 删除。")

@dp.message(commands=["add"])
async def cmd_add(message: types.Message):
    try:
        _, cron, msg = message.text.split(" ", 2)
        job_id = f"{message.chat.id}_{len(scheduled_jobs)}"
        trigger = CronTrigger.from_crontab(cron)

        def send_message(chat_id=message.chat.id, text=msg):
            asyncio.create_task(bot.send_message(chat_id, text))

        scheduler.add_job(send_message, trigger=trigger, id=job_id)
        scheduled_jobs[job_id] = (cron, msg)
        await message.answer(f"✅ 添加定时任务成功：\n时间: `{cron}`\n内容: {msg}", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ 添加失败：请使用格式 `/add <crontab> <内容>`\n示例：`/add */1 * * * * 每分钟播报一次`", parse_mode="Markdown")

@dp.message(commands=["list"])
async def cmd_list(message: types.Message):
    result = ""
    for job_id, (cron, msg) in scheduled_jobs.items():
        if job_id.startswith(str(message.chat.id)):
            result += f"🕒 `{job_id}` - `{cron}`\n📢 {msg}\n\n"
    await message.answer(result or "暂无定时任务", parse_mode="Markdown")

@dp.message(commands=["delete"])
async def cmd_delete(message: types.Message):
    try:
        _, job_id = message.text.split(" ", 1)
        scheduler.remove_job(job_id)
        scheduled_jobs.pop(job_id, None)
        await message.answer(f"✅ 删除任务 `{job_id}` 成功", parse_mode="Markdown")
    except Exception:
        await message.answer("❌ 删除失败，请使用格式：`/delete <job_id>`", parse_mode="Markdown")

# 运行 FastAPI 应用（使用 uvicorn 启动）