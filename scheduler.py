from apscheduler.schedulers.background import BackgroundScheduler
from database import get_active_schedules
from handlers import send_scheduled_message
import datetime

scheduler = BackgroundScheduler()

def schedule_job(job):
    scheduler.add_job(
        send_scheduled_message,
        'interval',
        hours=job['interval'],
        start_date=job['start_time'],
        end_date=job['end_time'],
        args=[job],
        id=job['id'],
        replace_existing=True
    )

def start_scheduler():
    scheduler.start()
    for job in get_active_schedules():
        schedule_job(job)