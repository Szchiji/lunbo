from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes, ConversationHandler
from db import fetch_schedules, create_schedule, fetch_schedule, update_schedule, delete_schedule

ADD_TEXT, ADD_MEDIA, ADD_BUTTON, ADD_REPEAT, ADD_PERIOD, ADD_START_DATE, ADD_END_DATE, ADD_CONFIRM = range(8)
EDIT_MENU, EDIT_TEXT, EDIT_MEDIA, EDIT_BUTTON, EDIT_REPEAT, EDIT_PERIOD, EDIT_START_DATE, EDIT_END_DATE, EDIT_CONFIRM = range(8, 17)

def cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ 取消", callback_data="cancel")]])

# --------- 添加流程 ---------

async def add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("请输入定时消息文本内容，或点击取消：", reply_markup=cancel_keyboard())
    context.user_data['new_schedule'] = {}
    return ADD_MEDIA

async def add_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_schedule']['text'] = update.message.text
    await update.message.reply_text("如需添加图片/视频，请直接发送媒体，否则回复“无”或点击取消：", reply_markup=cancel_keyboard())
    return ADD_BUTTON

async def add_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 处理媒体
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data['new_schedule']['media_type'] = 'photo'
        context.user_data['new_schedule']['media_file_id'] = file_id
    elif update.message.video:
        file_id = update.message.video.file_id
        context.user_data['new_schedule']['media_type'] = 'video'
        context.user_data['new_schedule']['media_file_id'] = file_id
    elif update.message.text and update.message.text.strip() != '无':
        context.user_data['new_schedule']['media_type'] = ''
        context.user_data['new_schedule']['media_file_id'] = ''
    else:
        context.user_data['new_schedule']['media_type'] = ''
        context.user_data['new_schedule']['media_file_id'] = ''
    await update.message.reply_text("请发送按钮文本（如有），或回复“无”：", reply_markup=cancel_keyboard())
    return ADD_REPEAT

async def add_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn_text = update.message.text.strip()
    if btn_text and btn_text != "无":
        context.user_data['new_schedule']['button_text'] = btn_text
        await update.message.reply_text("请发送按钮跳转链接：", reply_markup=cancel_keyboard())
        context.user_data['awaiting_btn_url'] = True
        return ADD_REPEAT
    elif context.user_data.get('awaiting_btn_url'):
        context.user_data['new_schedule']['button_url'] = btn_text
        del context.user_data['awaiting_btn_url']
        await update.message.reply_text("请发送重复周期（秒），如 86400 表示每天一次：", reply_markup=cancel_keyboard())
        return ADD_PERIOD
    else:
        context.user_data['new_schedule']['button_text'] = ''
        context.user_data['new_schedule']['button_url'] = ''
        await update.message.reply_text("请发送重复周期（秒），如 86400 表示每天一次：", reply_markup=cancel_keyboard())
        return ADD_PERIOD

async def add_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_schedule']['repeat_seconds'] = int(update.message.text)
    await update.message.reply_text("请发送周期描述，如 '每天' 或 '每周'：", reply_markup=cancel_keyboard())
    return ADD_START_DATE

async def add_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_schedule']['time_period'] = update.message.text
    await update.message.reply_text("请发送开始日期（YYYY-MM-DD），或回复“无”：", reply_markup=cancel_keyboard())
    return ADD_END_DATE

async def add_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_schedule']['start_date'] = update.message.text if update.message.text != '无' else ''
    await update.message.reply_text("请发送结束日期（YYYY-MM-DD），或回复“无”：", reply_markup=cancel_keyboard())
    return ADD_CONFIRM

async def add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_schedule']['end_date'] = update.message.text if update.message.text != '无' else ''
    sch = context.user_data['new_schedule']
    await create_schedule(update.effective_chat.id, sch)
    await update.message.reply_text("定时消息已添加成功！")
    return ConversationHandler.END

# --------- 编辑流程 ---------

async def show_schedule_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedules = await fetch_schedules(update.effective_chat.id)
    if not schedules:
        await update.message.reply_text("暂无定时消息。可用 /add_schedule 添加。")
        return
    keyboard = [[InlineKeyboardButton(f"{s['id']}: {s['text'][:10]}", callback_data=f"edit_{s['id']}")] for s in schedules]
    await update.message.reply_text("定时消息列表：", reply_markup=InlineKeyboardMarkup(keyboard + [[InlineKeyboardButton("取消", callback_data="cancel")]]))

async def edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("edit_"):
        s_id = int(query.data.split("_")[1])
        schedule = await fetch_schedule(s_id)
        context.user_data['edit_schedule'] = schedule
        keyboard = [
            [InlineKeyboardButton("文本", callback_data="edit_text"),
             InlineKeyboardButton("媒体", callback_data="edit_media")],
            [InlineKeyboardButton("按钮", callback_data="edit_button"),
             InlineKeyboardButton("周期", callback_data="edit_repeat")],
            [InlineKeyboardButton("期间", callback_data="edit_period")],
            [InlineKeyboardButton("开始日期", callback_data="edit_start"),
             InlineKeyboardButton("结束日期", callback_data="edit_end")],
            [InlineKeyboardButton("删除", callback_data="delete_schedule")],
            [InlineKeyboardButton("取消", callback_data="cancel")]
        ]
        await query.edit_message_text(
            f"编辑定时消息（ID: {s_id}）请选择要编辑的项：", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_MENU
    return ConversationHandler.END

async def edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("请输入新的文本内容：", reply_markup=cancel_keyboard())
    return EDIT_TEXT

async def save_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    s_id = context.user_data['edit_schedule']['id']
    await update_schedule(s_id, {"text": text})
    await update.message.reply_text("文本内容已修改。")
    return ConversationHandler.END

# 你可以仿照edit_text/save_edit_text实现edit_media、edit_button等其它字段的编辑

async def delete_schedule_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    s_id = context.user_data['edit_schedule']['id']
    await delete_schedule(s_id)
    await query.edit_message_text("消息已删除。")
    return ConversationHandler.END
