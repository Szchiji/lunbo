import logging
from apscheduler.schedulers.background import BackgroundScheduler
from db import fetch_schedules
from telegram import Bot

scheduler = BackgroundScheduler()

async def broadcast_task(bot: Bot, group_ids):
    for group_id in group_ids:
        schedules = await fetch_schedules(group_id)
        for schedule in schedules:
            if schedule['status']:
                try:
                    # 支持发送文本或媒体
                    if schedule['media_url']:
                        await bot.send_photo(chat_id=group_id, photo=schedule['media_url'], caption=schedule['text'])
                    else:
                        await bot.send_message(chat_id=group_id, text=schedule['text'])
                except Exception as e:
                    logging.exception(f"发送消息到 {group_id} 失败: {e}")

def schedule_broadcast_jobs(application, group_ids):
    scheduler.remove_all_jobs()
    scheduler.add_job(lambda: application.create_task(broadcast_task(application.bot, group_ids)), 'interval', seconds=60)
    scheduler.start()
    logging.info("定时轮播任务已启动")
