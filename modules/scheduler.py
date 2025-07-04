import re
from db import (
    fetch_schedules, fetch_schedule, create_schedule,
    update_schedule_multi, delete_schedule
)
from modules.keyboards import (
    schedule_list_menu, schedule_edit_menu, schedule_add_menu, group_select_menu
)
from config import GROUPS, ADMINS
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

(
    SELECT_GROUP, ADD_TEXT, ADD_MEDIA, ADD_BUTTON, ADD_REPEAT,
    ADD_PERIOD, ADD_START_DATE, ADD_END_DATE, ADD_CONFIRM,
    EDIT_TEXT, EDIT_MEDIA, EDIT_BUTTON, EDIT_REPEAT, EDIT_PERIOD, EDIT_START_DATE, EDIT_END_DATE
) = range(200, 216)

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMINS:
            if getattr(update, "message", None):
                await update.message.reply_text("无权限。")
            elif getattr(update, "callback_query", None):
                await update.callback_query.answer("无权限", show_alert=True)
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper

def parse_datetime_input(text):
    text = text.strip()
    if text in ["0", "留空", "不限", ""]:
        return ""
    m1 = re.match(r"^\d{4}-\d{2}-\d{2}$", text)
    m2 = re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$", text)
    if m1:
        return f"{text} 00:00"
    if m2:
        return text
    return None

async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, schedule_id: int, notice: str = ""):
    sch = await fetch_schedule(schedule_id)
    group_id = sch['chat_id'] if sch else None
    group_name = GROUPS.get(group_id, str(group_id)) if group_id else ""
    text = f"【定时消息设置】\nID: {schedule_id}\n群：{group_name}\n"
    if sch:
        text += (
            f"状态：{'启用' if sch.get('status') else '禁用'}\n"
            f"文本：{sch.get('text', '')}\n"
            f"媒体：{'有' if sch.get('media_url') else '无'}\n"
            f"按钮：{sch.get('button_text', '') or '无'}\n"
            f"重复：{sch.get('repeat_seconds', 0)//60}分钟\n"
            f"时间段：{sch.get('time_period', '全天')}\n"
            f"日期：{sch.get('start_date', '--')} ~ {sch.get('end_date', '--')}\n"
        )
    if notice:
        text = f"{notice}\n\n{text}"
    kb = schedule_edit_menu(sch, group_name) if sch else None
    if getattr(update, "message", None):
        await update.message.reply_text(text, reply_markup=kb)
    elif getattr(update, "callback_query", None):
        await update.callback_query.edit_message_text(text, reply_markup=kb)

@admin_only
async def show_schedule_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        group_id = context.user_data.get("selected_group_id")
        if not group_id:
            if getattr(update, "message", None):
                await update.message.reply_text("请选择要管理的群聊：", reply_markup=group_select_menu(GROUPS))
            elif getattr(update, "callback_query", None):
                await update.callback_query.edit_message_text("请选择要管理的群聊：", reply_markup=group_select_menu(GROUPS))
            return SELECT_GROUP
        schedules = await fetch_schedules(group_id)
        group_name = GROUPS.get(group_id) or str(group_id)
        if getattr(update, "message", None):
            await update.message.reply_text(f"⏰ [{group_name}] 定时消息列表：\n点击条目可设置。", reply_markup=schedule_list_menu(schedules))
        elif getattr(update, "callback_query", None):
            await update.callback_query.edit_message_text(f"⏰ [{group_name}] 定时消息列表：\n点击条目可设置。", reply_markup=schedule_list_menu(schedules))
    else:
        chat_id = chat.id
        schedules = await fetch_schedules(chat_id)
        await update.message.reply_text("⏰ 定时消息列表：\n点击条目可设置。", reply_markup=schedule_list_menu(schedules))
    return ConversationHandler.END

@admin_only
async def select_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("set_group_"):
        group_id = int(data[len("set_group_"):])
        context.user_data["selected_group_id"] = group_id
        group_title = GROUPS.get(group_id) or str(group_id)
        schedules = await fetch_schedules(group_id)
        await query.edit_message_text(
            f"⏰ [{group_title}] 定时消息列表：\n点击条目可设置。",
            reply_markup=schedule_list_menu(schedules)
        )
        return ConversationHandler.END
    await query.answer("请选择群聊")
    return SELECT_GROUP

@admin_only
async def entry_add_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = context.user_data.get("selected_group_id")
    if not group_id:
        if getattr(update, "callback_query", None):
            await update.callback_query.edit_message_text("请选择要设置定时消息的群聊：", reply_markup=group_select_menu(GROUPS))
        elif getattr(update, "message", None):
            await update.message.reply_text("请选择要设置定时消息的群聊：", reply_markup=group_select_menu(GROUPS))
        return SELECT_GROUP
    context.user_data["new_schedule"] = {}
    if getattr(update, "callback_query", None):
        await update.callback_query.edit_message_text("请输入文本内容：")
    else:
        await update.message.reply_text("请输入文本内容：")
    return ADD_TEXT

@admin_only
async def add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_schedule']['text'] = update.message.text.strip()
    await update.message.reply_text("请发送媒体（图片/视频/文件ID/URL），或输入“无”跳过：")
    return ADD_MEDIA

@admin_only
async def add_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media = ""
    media_type = ""
    if update.message.video:
        media = update.message.video.file_id
        media_type = "video"
    elif update.message.photo:
        media = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.document:
        media = update.message.document.file_id
        media_type = "document"
    elif update.message.text and update.message.text.strip().lower() != "无":
        media = update.message.text.strip()
        media_type = ""
    context.user_data['new_schedule']['media_url'] = media
    context.user_data['new_schedule']['media_type'] = media_type
    await update.message.reply_text("请输入按钮文字和链接，用英文逗号分隔，如：更多内容,https://example.com\n如无需按钮请输入“无”：")
    return ADD_BUTTON

@admin_only
async def add_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "无":
        context.user_data['new_schedule']['button_text'] = ""
        context.user_data['new_schedule']['button_url'] = ""
    else:
        try:
            btn_text, btn_url = text.split(",", 1)
            context.user_data['new_schedule']['button_text'] = btn_text.strip()
            context.user_data['new_schedule']['button_url'] = btn_url.strip()
        except Exception:
            await update.message.reply_text("格式错误，请用英文逗号隔开，如：按钮文字,https://xxx.com\n如无需按钮请输入“无”。")
            return ADD_BUTTON
    await update.message.reply_text("请输入重复时间，单位分钟（如60）：")
    return ADD_REPEAT

@admin_only
async def add_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text.strip())
        context.user_data['new_schedule']['repeat_seconds'] = minutes * 60
    except Exception:
        await update.message.reply_text("请输入整数分钟数。")
        return ADD_REPEAT
    await update.message.reply_text("请输入时间段，格式如 09:00-18:00 或留空全天：")
    return ADD_PERIOD

@admin_only
async def add_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    period = update.message.text.strip()
    if period in ["0", "留空", "不限", ""]:
        period = ""
    elif not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", period):
        await update.message.reply_text("格式错误，示例：09:00-18:00 或留空全天")
        return ADD_PERIOD
    context.user_data['new_schedule']['time_period'] = period
    await update.message.reply_text("请输入开始日期，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限：")
    return ADD_START_DATE

@admin_only
async def add_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    dt = parse_datetime_input(text)
    if dt is None:
        await update.message.reply_text("格式错误，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限。")
        return ADD_START_DATE
    context.user_data['new_schedule']['start_date'] = dt
    await update.message.reply_text("请输入结束日期，格式如 2025-06-30 或 2025-06-30 23:59，或留空不限：")
    return ADD_END_DATE

@admin_only
async def add_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    dt = parse_datetime_input(text)
    if dt is None:
        await update.message.reply_text("格式错误，格式如 2025-06-30 或 2025-06-30 23:59，或留空不限。")
        return ADD_END_DATE
    context.user_data['new_schedule']['end_date'] = dt
    sch = context.user_data['new_schedule']
    desc = (
        "【确认添加定时消息】\n"
        f"文本：{sch.get('text','')}\n"
        f"媒体：{'✔️' if sch.get('media_url') else '✖️'}\n"
        f"按钮：{('✔️' if sch.get('button_text') else '✖️')}\n"
        f"重复：每{sch.get('repeat_seconds',0)//60}分钟\n"
        f"时间段：{sch.get('time_period','全天')}\n"
        f"日期：{sch.get('start_date','--')} ~ {sch.get('end_date','--')}\n\n"
        "请点击“保存”按钮确认添加，或点击“取消”放弃。"
    )
    await update.message.reply_text(desc, reply_markup=schedule_add_menu(step="confirm"))
    return ADD_CONFIRM

@admin_only
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "confirm_save":
        group_id = context.user_data.get('selected_group_id')
        sch = context.user_data.get('new_schedule')
        if not group_id or not sch:
            await query.edit_message_text("群聊或消息内容缺失，无法保存。")
            return ConversationHandler.END
        await create_schedule(group_id, sch)
        await query.edit_message_text("定时消息已添加。")
        context.user_data.pop("new_schedule", None)
        return ConversationHandler.END
    elif query.data == "cancel_add":
        await query.edit_message_text("已取消添加。")
        context.user_data.pop("new_schedule", None)
        return ConversationHandler.END
    else:
        await query.answer("未知操作")
        return ADD_CONFIRM

@admin_only
async def add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in ["保存", "确认"]:
        group_id = context.user_data.get('selected_group_id')
        sch = context.user_data['new_schedule']
        await create_schedule(group_id, sch)
        await update.message.reply_text("定时消息已添加。")
        context.user_data.pop("new_schedule", None)
        return ConversationHandler.END
    elif text in ["取消"]:
        await update.message.reply_text("已取消添加。")
        context.user_data.pop("new_schedule", None)
        return ConversationHandler.END
    else:
        await update.message.reply_text("请点击“保存”按钮确认添加，或点击“取消”放弃。")
        return ADD_CONFIRM

@admin_only
async def edit_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    context.user_data["edit_schedule_id"] = schedule_id
    await show_edit_menu(update, context, schedule_id=schedule_id)
    return ConversationHandler.END

@admin_only
async def edit_text_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    context.user_data["edit_schedule_id"] = schedule_id
    await update.callback_query.edit_message_text("请输入新的文本内容：")
    return EDIT_TEXT

@admin_only
async def edit_text_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    new_text = update.message.text.strip()
    await update_schedule_multi(schedule_id, text=new_text, last_sent_time=None)
    sch = await fetch_schedule(schedule_id)
    if sch and sch['text'] == new_text:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="✅ 文本已成功修改。")
    else:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="⚠️ 文本未修改成功，请重试。")
    return ConversationHandler.END

@admin_only
async def edit_media_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    context.user_data["edit_schedule_id"] = schedule_id
    await update.callback_query.edit_message_text("请发送新的媒体（图片/视频/文件ID/URL），或输入“无”以删除：")
    return EDIT_MEDIA

@admin_only
async def edit_media_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    media = ""
    media_type = ""
    if update.message.video:
        media = update.message.video.file_id
        media_type = "video"
    elif update.message.photo:
        media = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.document:
        media = update.message.document.file_id
        media_type = "document"
    elif update.message.text and update.message.text.strip().lower() != "无":
        media = update.message.text.strip()
        media_type = ""
    await update_schedule_multi(schedule_id, media_url=media, media_type=media_type, last_sent_time=None)
    sch = await fetch_schedule(schedule_id)
    if sch and sch['media_url'] == media:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="✅ 媒体已成功修改。")
    else:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="⚠️ 媒体未修改成功，请重试。")
    return ConversationHandler.END

@admin_only
async def edit_button_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    context.user_data["edit_schedule_id"] = schedule_id
    await update.callback_query.edit_message_text("请输入新的按钮文字,链接，用英文逗号分隔，如：更多内容,https://example.com\n或输入“无”以删除：")
    return EDIT_BUTTON

@admin_only
async def edit_button_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    text = update.message.text.strip()
    if text.lower() == "无":
        await update_schedule_multi(schedule_id, button_text="", button_url="", last_sent_time=None)
        sch = await fetch_schedule(schedule_id)
        if sch and not sch['button_text'] and not sch['button_url']:
            await show_edit_menu(update, context, schedule_id=schedule_id, notice="✅ 按钮已删除。")
        else:
            await show_edit_menu(update, context, schedule_id=schedule_id, notice="⚠️ 按钮未成功删除，请重试。")
        return ConversationHandler.END
    try:
        btn_text, btn_url = text.split(",", 1)
    except Exception:
        await update.message.reply_text("格式错误，请用英文逗号隔开，如：按钮文字,https://xxx.com。")
        return EDIT_BUTTON
    await update_schedule_multi(schedule_id, button_text=btn_text.strip(), button_url=btn_url.strip(), last_sent_time=None)
    sch = await fetch_schedule(schedule_id)
    if sch and sch['button_text'] == btn_text.strip() and sch['button_url'] == btn_url.strip():
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="✅ 按钮已修改。")
    else:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="⚠️ 按钮未修改成功，请重试。")
    return ConversationHandler.END

@admin_only
async def edit_repeat_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    context.user_data["edit_schedule_id"] = schedule_id
    await update.callback_query.edit_message_text("请输入新的重复时间，单位分钟（如60）：")
    return EDIT_REPEAT

@admin_only
async def edit_repeat_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    try:
        minutes = int(update.message.text.strip())
    except Exception:
        await update.message.reply_text("请输入整数分钟数。")
        return EDIT_REPEAT
    await update_schedule_multi(schedule_id, repeat_seconds=minutes*60, last_sent_time=None)
    sch = await fetch_schedule(schedule_id)
    if sch and sch['repeat_seconds'] == minutes*60:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="✅ 重复时间已修改。")
    else:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="⚠️ 重复时间未修改成功，请重试。")
    return ConversationHandler.END

@admin_only
async def edit_period_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    context.user_data["edit_schedule_id"] = schedule_id
    await update.callback_query.edit_message_text("请输入新的时间段，格式如 09:00-18:00 或留空全天：")
    return EDIT_PERIOD

@admin_only
async def edit_period_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    period = update.message.text.strip()
    if period in ["0", "留空", "不限", ""]:
        period = ""
    elif not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", period):
        await update.message.reply_text("格式错误，示例：09:00-18:00 或留空全天")
        return EDIT_PERIOD
    await update_schedule_multi(schedule_id, time_period=period, last_sent_time=None)
    sch = await fetch_schedule(schedule_id)
    if sch and sch['time_period'] == period:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="✅ 时间段已修改。")
    else:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="⚠️ 时间段未修改成功，请重试。")
    return ConversationHandler.END

@admin_only
async def edit_start_date_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    context.user_data["edit_schedule_id"] = schedule_id
    await update.callback_query.edit_message_text("请输入新的开始日期，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限：")
    return EDIT_START_DATE

@admin_only
async def edit_start_date_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    text = update.message.text.strip()
    dt = parse_datetime_input(text)
    if dt is None:
        await update.message.reply_text("格式错误，格式如 2025-06-12 或 2025-06-12 09:30，或留空不限。")
        return EDIT_START_DATE
    await update_schedule_multi(schedule_id, start_date=dt, last_sent_time=None)
    sch = await fetch_schedule(schedule_id)
    if sch and sch['start_date'] == dt:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="✅ 开始日期已修改。")
    else:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="⚠️ 开始日期未修改成功，请重试。")
    return ConversationHandler.END

@admin_only
async def edit_end_date_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    context.user_data["edit_schedule_id"] = schedule_id
    await update.callback_query.edit_message_text("请输入新的结束日期，格式如 2025-06-30 或 2025-06-30 23:59，或留空不限：")
    return EDIT_END_DATE

@admin_only
async def edit_end_date_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = context.user_data.get("edit_schedule_id")
    text = update.message.text.strip()
    dt = parse_datetime_input(text)
    if dt is None:
        await update.message.reply_text("格式错误，格式如 2025-06-30 或 2025-06-30 23:59，或留空不限。")
        return EDIT_END_DATE
    await update_schedule_multi(schedule_id, end_date=dt, last_sent_time=None)
    sch = await fetch_schedule(schedule_id)
    if sch and sch['end_date'] == dt:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="✅ 结束日期已修改。")
    else:
        await show_edit_menu(update, context, schedule_id=schedule_id, notice="⚠️ 结束日期未修改成功，请重试。")
    return ConversationHandler.END

@admin_only
async def toggle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    sch = await fetch_schedule(schedule_id)
    new_status = 0 if sch.get("status") else 1
    await update_schedule_multi(schedule_id, status=new_status, last_sent_time=None)
    sch2 = await fetch_schedule(schedule_id)
    msg = "✅ 已启用" if sch2 and sch2.get("status") else "⛔ 已关闭"
    await update.callback_query.answer(msg)
    await show_edit_menu(update, context, schedule_id=schedule_id, notice=msg)

@admin_only
async def toggle_remove_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    sch = await fetch_schedule(schedule_id)
    new_val = 0 if sch.get("remove_last") else 1
    await update_schedule_multi(schedule_id, remove_last=new_val, last_sent_time=None)
    sch2 = await fetch_schedule(schedule_id)
    msg = "✅ 删除上一条：已开" if sch2 and sch2.get("remove_last") else "⛔ 删除上一条：已关"
    await update.callback_query.answer(msg)
    await show_edit_menu(update, context, schedule_id=schedule_id, notice=msg)

@admin_only
async def toggle_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    sch = await fetch_schedule(schedule_id)
    new_val = 0 if sch.get("pin") else 1
    await update_schedule_multi(schedule_id, pin=new_val, last_sent_time=None)
    sch2 = await fetch_schedule(schedule_id)
    msg = "✅ 置顶：已开" if sch2 and sch2.get("pin") else "⛔ 置顶：已关"
    await update.callback_query.answer(msg)
    await show_edit_menu(update, context, schedule_id=schedule_id, notice=msg)

@admin_only
async def delete_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_id = int(update.callback_query.data.split("_")[-1])
    await delete_schedule(schedule_id)
    await update.callback_query.edit_message_text("定时消息已删除。")
