from telegram import (
    Update, InputMediaPhoto, InputMediaVideo, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
)
from telegram.ext import (
    CommandHandler, MessageHandler, Filters, CallbackContext,
    ConversationHandler, CallbackQueryHandler
)
from uuid import uuid4
from database import add_schedule, get_active_schedules, deactivate_schedule, get_schedule_by_id, update_schedule
from scheduler import scheduler, schedule_job
import os
import json
from datetime import datetime

# 状态定义
(
    ADD_MEDIA,
    ADD_TEXT,
    ADD_BUTTONS,
    ADD_INTERVAL,
    ADD_START,
    ADD_END,
    CONFIRM,
    EDIT_SELECT,
    EDIT_FIELD,
) = range(9)

# 临时存储用户状态数据，生产环境可换成Redis等
user_data_temp = {}

def register_handlers(dispatcher):
    # 引导式添加任务
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addschedule', addschedule_start)],
        states={
            ADD_MEDIA: [MessageHandler(Filters.photo | Filters.video | Filters.document.mime_type("video/mp4"), add_media)],
            ADD_TEXT: [MessageHandler(Filters.text & ~Filters.command, add_text)],
            ADD_BUTTONS: [MessageHandler(Filters.text & ~Filters.command, add_buttons)],
            ADD_INTERVAL: [MessageHandler(Filters.text & ~Filters.command, add_interval)],
            ADD_START: [MessageHandler(Filters.text & ~Filters.command, add_start)],
            ADD_END: [MessageHandler(Filters.text & ~Filters.command, add_end)],
            CONFIRM: [MessageHandler(Filters.regex('^(确认|取消)$'), confirm_task)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(conv_handler)

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('tasks', show_tasks))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 欢迎使用定时消息 Bot！\n"
        "命令列表：\n"
        "/addschedule - 添加新定时任务\n"
        "/tasks - 查看定时任务列表\n"
        "/cancel - 取消当前操作"
    )

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "/addschedule - 添加任务\n"
        "/tasks - 查看任务列表\n"
        "/cancel - 取消当前操作"
    )

def addschedule_start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "请发送定时任务的媒体文件（图片/视频），或者发送“跳过”直接输入文本内容。"
    )
    user_data_temp[update.message.chat_id] = {}
    return ADD_MEDIA

def add_media(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = user_data_temp.get(chat_id, {})
    if update.message.text and update.message.text.lower() == '跳过':
        data['message_type'] = 'text'
        data['file_id'] = None
        update.message.reply_text("请输入任务的文字内容：")
        user_data_temp[chat_id] = data
        return ADD_TEXT
    elif update.message.photo:
        photo = update.message.photo[-1]
        data['message_type'] = 'photo'
        data['file_id'] = photo.file_id
    elif update.message.video:
        video = update.message.video
        data['message_type'] = 'video'
        data['file_id'] = video.file_id
    else:
        update.message.reply_text("请发送图片/视频文件，或发送“跳过”跳过此步骤。")
        return ADD_MEDIA

    update.message.reply_text("请输入任务的文字内容（可为空，直接发送空白即可）：")
    user_data_temp[chat_id] = data
    return ADD_TEXT

def add_text(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = user_data_temp.get(chat_id, {})
    text = update.message.text or ""
    data['content'] = text.strip()
    update.message.reply_text(
        "请输入按钮配置（格式示例：按钮文本1,按钮链接1;按钮文本2,按钮链接2），或者发送“无”跳过。"
    )
    user_data_temp[chat_id] = data
    return ADD_BUTTONS

def add_buttons(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = user_data_temp.get(chat_id, {})
    text = update.message.text.strip()
    if text == '无':
        data['buttons'] = ''
    else:
        # 解析按钮文本
        try:
            buttons = []
            parts = text.split(';')
            for part in parts:
                label, url = part.split(',', 1)
                buttons.append({'text': label.strip(), 'url': url.strip()})
            data['buttons'] = json.dumps(buttons, ensure_ascii=False)
        except Exception:
            update.message.reply_text("按钮格式错误，请重新输入，格式示例：按钮文本1,按钮链接1;按钮文本2,按钮链接2")
            return ADD_BUTTONS
    update.message.reply_text("请输入任务执行间隔（小时），例如：2")
    user_data_temp[chat_id] = data
    return ADD_INTERVAL

def add_interval(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = user_data_temp.get(chat_id, {})
    try:
        interval = int(update.message.text.strip())
        if interval <= 0:
            raise ValueError
        data['interval'] = interval
    except Exception:
        update.message.reply_text("请输入有效的正整数间隔（小时）")
        return ADD_INTERVAL
    update.message.reply_text("请输入任务开始时间，格式：YYYY-MM-DD HH:MM，或发送“现在”立即开始")
    user_data_temp[chat_id] = data
    return ADD_START

def add_start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = user_data_temp.get(chat_id, {})
    text = update.message.text.strip()
    if text == "现在":
        data['start_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        try:
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
            data['start_time'] = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            update.message.reply_text("时间格式错误，请重新输入，格式：YYYY-MM-DD HH:MM，或发送“现在”")
            return ADD_START
    update.message.reply_text("请输入任务结束时间，格式：YYYY-MM-DD HH:MM，或发送“无限”不设置结束时间")
    user_data_temp[chat_id] = data
    return ADD_END

def add_end(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = user_data_temp.get(chat_id, {})
    text = update.message.text.strip()
    if text == "无限":
        data['end_time'] = None
    else:
        try:
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
            data['end_time'] = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            update.message.reply_text("时间格式错误，请重新输入，格式：YYYY-MM-DD HH:MM，或发送“无限”")
            return ADD_END

    # 预览确认
    preview_text = "请确认定时任务信息：\n"
    preview_text += f"类型: {data['message_type']}\n"
    preview_text += f"文字内容: {data.get('content', '')}\n"
    btns = json.loads(data['buttons']) if data['buttons'] else []
    if btns:
        preview_text += "按钮:\n"
        for b in btns:
            preview_text += f"- {b['text']} -> {b['url']}\n"
    else:
        preview_text += "按钮: 无\n"
    preview_text += f"间隔: {data['interval']} 小时\n"
    preview_text += f"开始时间: {data['start_time']}\n"
    preview_text += f"结束时间: {data['end_time'] or '无限'}\n"
    preview_text += "发送“确认”保存任务，发送“取消”放弃。"

    update.message.reply_text(preview_text)
    user_data_temp[chat_id] = data
    return CONFIRM

def confirm_task(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    if text == "确认":
        data = user_data_temp.get(chat_id)
        task_id = str(uuid4())
        # 保存数据库
        add_schedule({
            'id': task_id,
            'chat_id': chat_id,
            'message_type': data['message_type'],
            'content': data.get('content', ''),
            'file_path': data.get('file_id', ''),
            'buttons': data.get('buttons', ''),
            'interval': data['interval'],
            'start_time': data['start_time'],
            'end_time': data['end_time'] or None,
        })
        # 添加定时任务
        schedule_job({
            'id': task_id,
            'chat_id': chat_id,
            'message_type': data['message_type'],
            'content': data.get('content', ''),
            'file_path': data.get('file_id', ''),
            'buttons': data.get('buttons', ''),
            'interval': data['interval'],
            'start_time': data['start_time'],
            'end_time': data['end_time'] or None,
        })
        update.message.reply_text("✅ 定时任务已保存并启用！")
        user_data_temp.pop(chat_id, None)
        return ConversationHandler.END
    else:
        update.message.reply_text("操作已取消。")
        user_data_temp.pop(chat_id, None)
        return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_data_temp.pop(chat_id, None)
    update.message.reply_text("已取消当前操作。")
    return ConversationHandler.END

def show_tasks(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    tasks = get_active_schedules()
    if not tasks:
        update.message.reply_text("没有活跃的定时任务。")
        return
    text = "📋 当前定时任务列表：\n"
    keyboard = []
    for t in tasks:
        if t['chat_id'] != chat_id:
            continue
        text += f"- ID: {t['id'][:8]}  间隔: {t['interval']}小时  开始: {t['start_time']}\n"
        keyboard.append([
            InlineKeyboardButton(f"详情 {t['id'][:8]}", callback_data=f"detail_{t['id']}"),
            InlineKeyboardButton("删除", callback_data=f"delete_{t['id']}"),
            InlineKeyboardButton("修改", callback_data=f"edit_{t['id']}")
        ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text, reply_markup=reply_markup)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data.startswith("detail_"):
        task_id = data[7:]
        task = get_schedule_by_id(task_id)
        if not task:
            query.edit_message_text("任务不存在或已删除。")
            return
        text = f"📄 任务详情\nID: {task['id']}\n间隔: {task['interval']}小时\n开始: {task['start_time']}\n结束: {task['end_time'] or '无限'}\n内容: {task['content']}"
        btns = json.loads(task['buttons']) if task['buttons'] else []
        if btns:
            text += "\n按钮：\n"
            for b in btns:
                text += f"- {b['text']} -> {b['url']}\n"
        query.edit_message_text(text)

    elif data.startswith("delete_"):
        task_id = data[7:]
        deactivate_schedule(task_id)
        # 取消定时任务
        try:
            scheduler.remove_job(task_id)
        except Exception:
            pass
        query.edit_message_text(f"任务 {task_id[:8]} 已删除。")

    elif data.startswith("edit_"):
        task_id = data[5:]
        task = get_schedule_by_id(task_id)
        if not task:
            query.edit_message_text("任务不存在或已删除。")
            return
        user_data_temp[chat_id] = task
        query.message.reply_text("请输入新的文字内容（发送空白保持不变）：")
        context.user_data['edit_id'] = task_id
        return EDIT_FIELD

def edit_field(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    task_id = context.user_data.get('edit_id')
    if not task_id:
        update.message.reply_text("编辑任务失败，未找到任务ID。")
        return ConversationHandler.END
    task = user_data_temp.get(chat_id, {})
    text = update.message.text.strip()
    if text:
        task['content'] = text
    update.message.reply_text("请输入新的间隔时间（小时，空白保持不变）：")
    user_data_temp[chat_id] = task
    return EDIT_FIELD

# 这里省略完整修改流程代码，需按需求补充（可多步问答完成修改）

# 发送定时消息函数
def send_scheduled_message(job):
    chat_id = job['chat_id']
    bot = job.get('bot')  # 如果传入bot，否则从外部获得
    if not bot:
        return
    buttons = []
    if job['buttons']:
        try:
            btns = json.loads(job['buttons'])
            buttons = [[InlineKeyboardButton(b['text'], url=b['url'])] for b in btns]
        except Exception:
            buttons = []
    markup = InlineKeyboardMarkup(buttons) if buttons else None

    try:
        if job['message_type'] == 'photo':
            bot.send_photo(chat_id=chat_id, photo=job['file_path'], caption=job['content'], reply_markup=markup)
        elif job['message_type'] == 'video':
            bot.send_video(chat_id=chat_id, video=job['file_path'], caption=job['content'], reply_markup=markup)
        else:
            bot.send_message(chat_id=chat_id, text=job['content'], reply_markup=markup)
    except Exception as e:
        print(f"发送消息失败: {e}")