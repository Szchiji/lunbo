from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import json

async def auto_reply_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["ar_step"] = 1
    await update.message.reply_text("请输入要触发的关键词：", reply_markup=ReplyKeyboardRemove())

async def auto_reply_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("ar_step", 1)
    text = update.message.text
    if step == 1:
        context.user_data["ar_keyword"] = text.strip()
        context.user_data["ar_step"] = 2
        await update.message.reply_text("请输入要回复的文本内容：")
    elif step == 2:
        context.user_data["ar_reply"] = text
        context.user_data["ar_step"] = 3
        keyboard = [
            [InlineKeyboardButton("无多媒体", callback_data="ar_media_none")],
            [InlineKeyboardButton("图片", callback_data="ar_media_photo")],
            [InlineKeyboardButton("视频", callback_data="ar_media_video")],
            [InlineKeyboardButton("音频", callback_data="ar_media_audio")],
            [InlineKeyboardButton("文档", callback_data="ar_media_doc")],
        ]
        await update.message.reply_text("请选择是否要添加多媒体：", reply_markup=InlineKeyboardMarkup(keyboard))
    elif step == 4:
        mtype = context.user_data.get("ar_mtype")
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
        context.user_data["ar_media"] = file_id
        context.user_data["ar_step"] = 5
        await ask_inline_buttons(update, context)
    elif step == 5:
        try:
            if text.strip().lower() == "无":
                context.user_data["ar_buttons"] = None
            else:
                btns = json.loads(text)
                assert isinstance(btns, list)
                context.user_data["ar_buttons"] = json.dumps(btns)
        except Exception:
            await update.message.reply_text("按钮格式错误，请输入JSON数组，如: \n[{'text':'官网','url':'https://baidu.com'}]\n如无需按钮可输入“无”。")
            return
        await save_auto_reply(update, context)
    else:
        await update.message.reply_text("流程已结束，若需重来请再点“添加自动回复”。")

async def auto_reply_media_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "ar_media_none":
        context.user_data["ar_mtype"] = None
        context.user_data["ar_media"] = None
        context.user_data["ar_step"] = 5
        await ask_inline_buttons(query, context, via_callback=True)
    else:
        mtype = data.replace("ar_media_", "")
        context.user_data["ar_mtype"] = mtype
        context.user_data["ar_step"] = 4
        await query.edit_message_text(f"请上传{mtype}文件：")

async def ask_inline_buttons(target, context, via_callback=False):
    msg = "如需添加内联按钮，请输入按钮JSON数组，格式如：\n[{'text':'点我','url':'https://baidu.com'}]\n如无需按钮，可直接发送“无”。"
    if via_callback:
        await target.edit_message_text(msg)
    else:
        await target.message.reply_text(msg)

async def save_auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kw = context.user_data.get("ar_keyword")
    reply = context.user_data.get("ar_reply")
    mtype = context.user_data.get("ar_mtype")
    media = context.user_data.get("ar_media")
    btns = context.user_data.get("ar_buttons")
    from plugins.db import add_auto_reply_db
    await add_auto_reply_db(update.effective_chat.id, kw, reply, mtype, media, btns)
    await update.message.reply_text("自动回复已设置成功！", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()

async def list_auto_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from plugins.db import get_auto_replies, toggle_auto_reply, delete_auto_reply
    rows = await get_auto_replies(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("无自动回复。")
        return
    msg = "自动回复列表：\n"
    for r in rows:
        status = "✅" if r["enabled"] else "❌"
        msg += f"{status} {r['keyword']} → {r['reply']}\n"
    await update.message.reply_text(msg + "\n发送 /toggle_reply 关键词 或 /del_reply 关键词 可开关/删除。")

# 支持命令 /toggle_reply 关键词 与 /del_reply 关键词
async def toggle_reply_cmd(update, context):
    if not context.args:
        await update.message.reply_text("用法: /toggle_reply 关键词")
        return
    kw = context.args[0]
    from plugins.db import toggle_auto_reply
    enabled = await toggle_auto_reply(update.effective_chat.id, kw)
    if enabled is not False:
        await update.message.reply_text(f"{kw} 已{'启用' if enabled else '关闭'}")
    else:
        await update.message.reply_text("未找到该自动回复。")

async def del_reply_cmd(update, context):
    if not context.args:
        await update.message.reply_text("用法: /del_reply 关键词")
        return
    kw = context.args[0]
    from plugins.db import delete_auto_reply
    await delete_auto_reply(update.effective_chat.id, kw)
    await update.message.reply_text("已删除。")

# 自动回复触发
async def auto_reply_handler(update, context):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    from plugins.db import get_enabled_auto_replies
    rows = await get_enabled_auto_replies(update.effective_chat.id)
    for r in rows:
        if r["keyword"] in text:
            reply_markup = None
            if r["buttons"]:
                btns = json.loads(r["buttons"])
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(b["text"], url=b["url"])] for b in btns])
            if r["media_type"] and r["media_url"]:
                if r["media_type"] == "photo":
                    await update.message.reply_photo(photo=r["media_url"], caption=r["reply"], reply_markup=reply_markup)
                elif r["media_type"] == "video":
                    await update.message.reply_video(video=r["media_url"], caption=r["reply"], reply_markup=reply_markup)
                elif r["media_type"] == "audio":
                    await update.message.reply_audio(audio=r["media_url"], caption=r["reply"], reply_markup=reply_markup)
                elif r["media_type"] == "document":
                    await update.message.reply_document(document=r["media_url"], caption=r["reply"], reply_markup=reply_markup)
            else:
                await update.message.reply_text(r["reply"], reply_markup=reply_markup)
            break
