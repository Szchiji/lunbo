from aiogram import Router, types, F
from scheduler import schedule_message, list_jobs, remove_job

router = Router()
user_jobs = {}

@router.message(F.text == "/start")
async def start(msg: types.Message):
    await msg.answer("欢迎使用定时发布 Bot！\n使用 /add 添加定时消息")

@router.message(F.text.startswith("/add"))
async def add(msg: types.Message):
    parts = msg.text.split(" ", 2)
    if len(parts) < 3:
        await msg.answer("格式错误，使用：/add 2025-05-30 12:00:00 消息内容")
        return
    time_str = parts[1] + " " + parts[2]
    content = parts[3] if len(parts) > 3 else "测试内容"
    job_id = f"{msg.chat.id}_{time_str}"

    success = schedule_message(chat_id=msg.chat.id, text=content, run_time=time_str, job_id=job_id)
    if success:
        await msg.answer(f"✅ 已添加定时消息：{time_str}")
    else:
        await msg.answer("❌ 时间格式错误，正确格式：2025-05-30 12:00:00")

@router.message(F.text == "/list")
async def list_scheduled(msg: types.Message):
    jobs = list_jobs(chat_id=msg.chat.id)
    if not jobs:
        await msg.answer("⛔ 没有找到定时消息")
    else:
        await msg.answer("📋 定时任务：\n" + "\n".join(jobs))

@router.message(F.text.startswith("/remove"))
async def remove(msg: types.Message):
    parts = msg.text.split(" ", 1)
    if len(parts) < 2:
        await msg.answer("请提供任务 ID，例如：/remove 123")
        return
    job_id = parts[1]
    removed = remove_job(job_id)
    if removed:
        await msg.answer("✅ 删除成功")
    else:
        await msg.answer("❌ 没有找到该任务")