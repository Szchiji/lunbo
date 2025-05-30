from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime
from bot_init import bot

scheduler = AsyncIOScheduler()
scheduler.start()

def schedule_message(chat_id: int, text: str, run_time: str, job_id: str):
    try:
        dt = datetime.strptime(run_time, "%Y-%m-%d %H:%M:%S")
        scheduler.add_job(send_message, 'date', run_date=dt, args=[chat_id, text], id=job_id)
        return True
    except ValueError:
        return False

async def send_message(chat_id: int, text: str):
    await bot.send_message(chat_id=chat_id, text=text)

def list_jobs(chat_id: int):
    return [job.id for job in scheduler.get_jobs() if str(chat_id) in job.id]

def remove_job(job_id: str):
    try:
        scheduler.remove_job(job_id)
        return True
    except JobLookupError:
        return False