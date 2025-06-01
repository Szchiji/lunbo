from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, Filters, ConversationHandler, CallbackContext
from datetime import datetime
import json
from db import add_schedule, list_schedules, get_schedule, delete_schedule, update_schedule
from utils import build_buttons, format_task_preview
from scheduler import schedule_job

(
    ADD_TEXT,
    ADD_MEDIA_TYPE,
    ADD_MEDIA,
    ADD_BUTTONS,
    ADD_INTERVAL,
    ADD_START,
    ADD_END,
    ADD_CONFIRM,

    EDIT_TEXT,
    EDIT_MEDIA_TYPE,
    EDIT_MEDIA,
    EDIT_BUTTONS,
    EDIT_INTERVAL,
    EDIT_START,
    EDIT_END,
    EDIT_CONFIRM
) = range(16)

# 添加流程
def start_add(update: Update, context: CallbackContext):
    update.message.reply_text("开始添加定时任务，请输入文字内容：")
    return ADD_TEXT

def add_text(update: Update, context: CallbackContext):
    context.user_data['new_task'] = {}
    context.user_data['new_task']['content'] = update.message.text
    update.message.reply_text("请问要发送什么类型的媒体？发送“文字”跳过媒体，发送“图片”或“视频”：")
    return ADD_MEDIA_TYPE

def add_media_type(update: Update, context: CallbackContext):
    media_type = update.message.text.lower()
    if media_type == '文字':
        context.user_data['new_task']['message_type'] = None
        context.user_data['new_task']['file_path'] = None
        update.message.reply_text("跳过媒体上传，接下来请输入按钮，格式JSON数组（例如：[{'text':'百度','url':'https://www.baidu.com'}]），或者发送“无”：")
        return ADD_BUTTONS
    elif media_type in ['图片', '视频']:
        context.user_data['new_task']['message_type'] = 'photo' if media_type == '图片' else 'video'
        update.message.reply_text(f"请发送{media_type}文件：")
        return ADD_MEDIA
    else:
        update.message.reply_text("输入无效，请输入“文字”、“图片”或“视频”：")
        return ADD_MEDIA_TYPE

def add_media(update: Update, context: CallbackContext):
    new_task = context.user_data['new_task']
    if new_task['message_type'] == 'photo' and update.message.photo:
        # 取最大尺寸图片
        photo = update.message.photo[-1]
        file = photo.get_file()
        file_path = f"./media/{file.file_id}.jpg"
        file.download(file_path)
        new_task['file_path'] = file_path
        update.message.reply_text("图片已保存，接下来请输入按钮，格式JSON数组或“无”：")
        return ADD_BUTTONS
    elif new_task['message_type'] == 'video' and update.message.video:
        video = update.message.video
        file = video.get_file()
        file_path = f"./media/{file.file_id}.mp4"
        file.download(file_path)
        new_task['file_path'] = file_path
        update.message.reply_text("视频已保存，接下来请输入按钮，格式JSON数组或“无”：")
        return ADD_BUTTONS
    else:
        update.message.reply_text(f"请发送正确的{new_task['message_type']}文件：")
        return ADD_MEDIA

def add_buttons(update: Update, context: CallbackContext):
    text = update.message.text
    if text.strip() == '无':
        context.user_data['new_task']['buttons'] = None
    else:
        try:
            # 验证json格式
            btn_list = json.loads(text.replace("'", '"'))
            # 简单验证格式
            if isinstance(btn_list, list):
                context.user_data['new_task']['buttons'] = json.dumps(btn_list)
            else:
                raise ValueError
        except:
            update.message.reply_text("按钮格式错误，请输入JSON数组，或者“无”：")
            return ADD_BUTTONS
    update.message.reply_text("请输入发送间隔（小时，整数）：")
    return ADD_INTERVAL

def add_interval(update: Update, context: CallbackContext):
    try:
        interval = int(update.message.text)
        if interval < 1:
            raise ValueError
        context.user_data['new_task']['interval'] = interval
        update.message.reply_text("请输入开始时间（格式：YYYY-MM-DD HH:MM:SS），或发送“现在”立即开始：")
        return ADD_START
    except:
        update.message.reply_text("请输入正确的整数小时间隔：")
        return ADD_INTERVAL

def add_start(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    if text == "现在":
        context.user_data['new_task']['start_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        try:
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            context.user_data['new_task']['start_time'] = text
        except:
            update.message.reply_text("时间格式错误，请输入“现在”或正确的开始时间（YYYY-MM-DD HH:MM:SS）：")
            return ADD_START
    update.message.reply_text("请输入结束时间（格式：YYYY-MM-DD HH:MM:SS），或发送“无限”：")
    return ADD_END

def add_end(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    if text == "无限":
        context.user_data['new_task']['end_time'] = None
    else:
        try:
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            context.user_data['new_task']['end_time'] = text
        except:
            update.message.reply_text("时间格式错误，请输入“无限”或正确的结束时间（YYYY-MM-DD HH:MM:SS）：")
            return ADD_END
    task = context.user_data['new_task']
    preview = format_task_preview({
        'id': '(待保存)',
        **task
    })
    update.message.reply_text(f"请确认任务信息：\n{preview}\n发送“确认”保存，发送“取消”放弃。")
    return ADD_CONFIRM

def add_confirm(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    if text == "确认":
        task = context.user_data['new_task']
        task['chat_id'] = update.effective_chat.id
        task_id = add_schedule(task)
        task['id'] = task_id
        update.message.reply_text(f"任务已保存，ID: {task_id}")

        # 调度任务
        schedule_job(context.bot, task)
        return ConversationHandler.END
    else:
        update.message.reply_text("任务添加已取消。")
        return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("操作已取消。")
    return ConversationHandler.END


# 任务列表查看与删除

def list_tasks(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    tasks = list_schedules(chat_id)
    if not tasks:
        update.message.reply_text("当前无定时任务。")
        return
    text = "当前任务列表：\n"
    for t in tasks:
        text += f"ID:{t['id']} 内容:{t['content'][:20]}...\n"
    update.message.reply_text(text)

def delete_task(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("用法：/delete_task 任务ID")
        return
    task_id = args[0]
    task = get_schedule(task_id)
    if not task:
        update.message.reply_text("任务不存在。")
        return
    delete_schedule(task_id)
    try:
        from scheduler import scheduler
        scheduler.remove_job(str(task_id))
    except Exception:
        pass
    update.message.reply_text(f"任务ID {task_id} 已删除。")