from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging

scheduler = BackgroundScheduler()
scheduler.start()

def send_telegram_message(context, task):
    bot = context.job.context['bot']
    chat_id = task['chat_id']

    # 判断是否超过结束时间
    if task['end_time']:
        end_dt = datetime.strptime(task['end_time'], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > end_dt:
            # 超过结束时间，移除任务
            job = context.job
            job.remove()
            return

    buttons = None
    if task.get('buttons'):
        import json
        try:
            btn_list = json.loads(task['buttons'])
            buttons = [[
                {
                    'text': btn['text'],
                    'url': btn['url']
                }
            ] for btn in btn_list]
            from telegram import InlineKeyboardMarkup
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton(b['text'], url=b['url']) for b in row] for row in buttons
            ])
        except Exception as e:
            logging.error(f"加载按钮失败：{e}")

    try:
        if task['message_type'] == 'photo' and task['file_path']:
            bot.send_photo(chat_id=chat_id, photo=task['file_path'], caption=task['content'], reply_markup=buttons)
        elif task['message_type'] == 'video' and task['file_path']:
            bot.send_video(chat_id=chat_id, video=task['file_path'], caption=task['content'], reply_markup=buttons)
        else:
            bot.send_message(chat_id=chat_id, text=task['content'], reply_markup=buttons)
    except Exception as e:
        logging.error(f"发送消息失败：{e}")

def schedule_job(bot, task):
    # 先移除已有任务
    job_id = str(task['id'])
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    # 计算首次触发时间
    start_time = datetime.strptime(task['start_time'], "%Y-%m-%d %H:%M:%S") if task.get('start_time') else datetime.now()

    trigger = IntervalTrigger(hours=task['interval'], start_date=start_time)

    scheduler.add_job(send_telegram_message, trigger, args=[task], id=job_id, replace_existing=True, kwargs={'context': {'bot': bot, 'task': task}})