from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot import bot

scheduler = AsyncIOScheduler()
scheduler.start()

def schedule_message(chat_id, text, run_date, job_id):
    scheduler.add_job(
        bot.send_message,
        trigger="date",
        run_date=run_date,
        args=[chat_id, text],
        id=job_id,
        replace_existing=True
    )

def remove_job(job_id):
    scheduler.remove_job(job_id)