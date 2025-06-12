import logging
from apscheduler.schedulers.background import BackgroundScheduler
from db import fetch_schedules
from telegram import Bot

scheduler = BackgroundScheduler()

async def broadcast_task(bot: Bot, group_ids):
    for group_id in group_ids:
        schedules = await fetch_schedules(group_id)
        for schedule in schedules:
            # 检查是否到达发送条件，这里仅演示，实际你可补充更多逻辑
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
    # 先移除所有旧任务，避免重复
    scheduler.remove_all_jobs()
    # 使用 PTB v20+ 推荐的 application.create_task 调度协程
    scheduler.add_job(lambda: application.create_task(broadcast_task(application.bot, group_ids)), 'interval', seconds=60)
    scheduler.start()
    logging.info("定时轮播任务已启动")
