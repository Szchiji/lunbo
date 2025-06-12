from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import json

async def schedule_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["sch_step"] = 1
    await update.message.reply_text("请输入cron表达式，如 0 9 * * * （每天9点）：")

async def schedule_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("sch_step", 1)
    text = update.message.text
    if step == 1:
        context.user_data["sch_cron"] = text.strip()
        context.user_data["sch_step"] = 2
        await update.message.reply_text("请输入推送内容:")
    elif step == 2:
        context.user_data["sch_content"] = text
        context.user_data["sch_step"] = 3
        keyboard = [
            [InlineKeyboardButton("无多媒体", callback_data="sch_media_none")],
            [InlineKeyboardButton("图片", callback_data="sch_media_photo")],
            [InlineKeyboardButton("视频", callback_data="sch_media_video")],
            [InlineKeyboardButton("音频", callback_data="sch_media_audio")],
            [InlineKeyboardButton("文档", callback_data="sch_media_doc")],
        ]
        await update.message.reply_text("请选择是否要添加多媒体：", reply_markup=InlineKeyboardMarkup(keyboard))
    elif step == 4:
        mtype = context.user_data.get("sch_mtype")
        file_id = None
        if mtype == "photo" and update.message.photo:
            file_id = update.message.photo[-1].file_id
        elif mtype == "video" and update.message.video:
            file_id = update.message.video.file_id
        elif mtype == "audio" and update.message.audio:
            file_id = update.message.audio.file_id
        elif mtype == "document" and update.message.document:
            file_id = update.message.document.file_id
        if not file_id:
            await update.message.reply_text("请上传正确的多媒体文件。")
            return
        context.user_data["sch_media"] = file_id
        context.user_data["sch_step"] = 5
        await ask_inline_buttons(update, context)
    elif step == 5:
        try:
            if text.strip().lower() == "无":
                context.user_data["sch_buttons"] = None
            else:
                btns = json.loads(text)
                assert isinstance(btns, list)
                context.user_data["sch_buttons"] = json.dumps(btns)
        except Exception:
            await update.message.reply_text("按钮格式错误，请输入JSON数组，如: \n[{'text':'官网','url':'https://baidu.com'}]\n如无需按钮可输入“无”。")
            return
        await save_schedule_msg(update, context)
    else:
        await update.message.reply_text("流程已结束，若需重来请再点“添加定时消息”。")

async def schedule_media_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "sch_media_none":
        context.user_data["sch_mtype"] = None
        context.user_data["sch_media"] = None
        context.user_data["sch_step"] = 5
        await ask_inline_buttons(query, context, via_callback=True)
    else:
        mtype = data.replace("sch_media_", "")
        context.user_data["sch_mtype"] = mtype
        context.user_data["sch_step"] = 4
        await query.edit_message_text(f"请上传{mtype}文件：")

async def ask_inline_buttons(target, context, via_callback=False):
    msg = "如需添加内联按钮，请输入按钮JSON数组，格式如：\n[{'text':'点我','url':'https://baidu.com'}]\n如无需按钮可直接发送“无”。"
    if via_callback:
        await target.edit_message_text(msg)
    else:
        await target.message.reply_text(msg)

async def save_schedule_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cron = context.user_data.get("sch_cron")
    content = context.user_data.get("sch_content")
    mtype = context.user_data.get("sch_mtype")
    media = context.user_data.get("sch_media")
    btns = context.user_data.get("sch_buttons")
    from plugins.db import add_schedule_db
    await add_schedule_db(update.effective_chat.id, content, cron, mtype, media, btns)
    await update.message.reply_text("定时消息已设置成功！", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()

async def list_schedule_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from plugins.db import get_schedules
    rows = await get_schedules(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("无定时消息。")
        return
    msg = "定时消息列表：\n"
    for r in rows:
        status = "✅" if r["enabled"] else "❌"
        msg += f"{status} [{r['cron']}] {r['content']}\n"
    await update.message.reply_text(msg + "\n发送 /toggle_timer ID 或 /del_timer ID 可开关/删除。")

async def toggle_timer_cmd(update, context):
    if not context.args:
        await update.message.reply_text("用法: /toggle_timer ID")
        return
    sid = int(context.args[0])
    from plugins.db import toggle_schedule
    enabled = await toggle_schedule(update.effective_chat.id, sid)
    if enabled is not False:
        await update.message.reply_text(f"定时消息已{'启用' if enabled else '关闭'}")
    else:
        await update.message.reply_text("未找到该定时消息。")

async def del_timer_cmd(update, context):
    if not context.args:
        await update.message.reply_text("用法: /del_timer ID")
        return
    sid = int(context.args[0])
    from plugins.db import delete_schedule
    await delete_schedule(update.effective_chat.id, sid)
    await update.message.reply_text("已删除。")
