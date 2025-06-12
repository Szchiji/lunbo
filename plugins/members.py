import datetime
from telegram import Update
from telegram.ext import ContextTypes
from plugins.db import add_member, remove_member, list_members, is_member

async def add_member_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("用法: /add_member 用户ID 天数(0=永久)")
        return
    user_id = int(context.args[0])
    days = int(context.args[1])
    expire_at = None if days == 0 else datetime.datetime.utcnow() + datetime.timedelta(days=days)
    await add_member(update.effective_chat.id, user_id, expire_at)
    await update.message.reply_text(f"已添加会员 {user_id}，到期：{expire_at.strftime('%Y-%m-%d %H:%M') if expire_at else '永久'}")

async def remove_member_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法: /remove_member 用户ID")
        return
    user_id = int(context.args[0])
    await remove_member(update.effective_chat.id, user_id)
    await update.message.reply_text(f"已移除会员 {user_id}")

async def list_members_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = await list_members(update.effective_chat.id)
    msg = "本群会员列表：\n"
    has = False
    for m in rows:
        has = True
        expire = m["expire_at"]
        expire_str = expire.strftime("%Y-%m-%d %H:%M") if expire else "永久"
        msg += f"- {m['user_id']}，到期：{expire_str}\n"
    if not has:
        msg += "无"
    await update.message.reply_text(msg)

async def is_member_func(chat_id, user_id):
    return await is_member(chat_id, user_id)
