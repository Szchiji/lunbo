
import os
from uuid import uuid4
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

TOKEN = os.getenv("BOT_TOKEN", "你的 Bot Token")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-domain.com/webhook")  # 用你自己的域名替换

# Bot 初始化
bot = Bot(token=TOKEN)
app = FastAPI()
application = Application.builder().token(TOKEN).build()

# 初始化 APScheduler
scheduler = AsyncIOScheduler()
scheduler.start()

# ✅ 定时消息发送函数
async def send_scheduled_message(chat_id, text):
    await bot.send_message(chat_id=chat_id, text=f"🕒 定时消息：\n\n{text}")

# ✅ 设置定时任务的命令（示例命令：/schedule 2025-05-30 22:00 Hello）
async def schedule_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 3:
            await update.message.reply_text("用法：/schedule YYYY-MM-DD HH:MM 消息内容")
            return

        date_str = context.args[0]
        time_str = context.args[1]
        text = " ".join(context.args[2:])
        run_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        job_id = f"{update.effective_chat.id}_{uuid4().hex[:8]}"
        
        scheduler.add_job(
            send_scheduled_message,
            trigger='date',
            run_date=run_time,
            args=[update.effective_chat.id, text],
            id=job_id
        )

        await update.message.reply_text(f"✅ 定时任务已添加：\n🕒 {run_time}\n🆔 `{job_id}`", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 错误：{str(e)}")

# ✅ 查看定时任务
async def list_scheduled(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = scheduler.get_jobs()
    if not jobs:
        await update.message.reply_text("当前没有已添加的定时消息。")
        return

    msg_lines = ["📋 当前定时任务列表："]
    for job in jobs:
        run_time = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else "未知"
        msg_lines.append(f"🆔 `{job.id}`\n🕒 {run_time}")

    await update.message.reply_text("\n\n".join(msg_lines), parse_mode='Markdown')

# ✅ 删除定时任务
async def delete_scheduled(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("请提供任务 ID，例如：\n/delete_scheduled job_id", parse_mode='Markdown')
        return

    job_id = context.args[0]
    job = scheduler.get_job(job_id)

    if job:
        job.remove()
        await update.message.reply_text(f"✅ 已删除任务：`{job_id}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ 未找到 ID 为 `{job_id}` 的任务。", parse_mode='Markdown')

# 添加命令处理器
application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("欢迎使用定时机器人！")))
application.add_handler(CommandHandler("schedule", schedule_message))
application.add_handler(CommandHandler("list_scheduled", list_scheduled))
application.add_handler(CommandHandler("delete_scheduled", delete_scheduled))

# ✅ Webhook 接收端点
@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}

# ✅ 启动 Webhook（FastAPI）
@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook()
    await bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook 已设置:", WEBHOOK_URL)