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
        update.message.reply_text("跳过媒体上传，接下来请输入按钮，格式JSON数组（例如：[{'