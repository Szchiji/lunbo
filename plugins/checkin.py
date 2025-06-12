import datetime
from telegram import Update
from telegram.ext import ContextTypes
from plugins.members import is_member_func

CHECKIN_RECORD = {}

def get_today():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.mention_html()
    if not await is_member_func(chat_id, user_id):
        await update.message.reply_text("只有会员才能打卡，请联系管理员。")
        return
    today = get_today()
    if chat_id not in CHECKIN_RECORD:
        CHECKIN_RECORD[chat_id] = {}
    if today not in CHECKIN_RECORD[chat_id]:
        CHECKIN_RECORD[chat_id][today] = set()
    if user_id in CHECKIN_RECORD[chat_id][today]:
        await update.message.reply_text("你今天已经打过卡啦！")
    else:
        CHECKIN_RECORD[chat_id][today].add(user_id)
        await update.message.reply_text(f"{username} 打卡成功！", parse_mode="HTML")

async def checkin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    today = get_today()
    if chat_id in CHECKIN_RECORD and today in CHECKIN_RECORD[chat_id] and CHECKIN_RECORD[chat_id][today]:
        mentions = []
        for user_id in CHECKIN_RECORD[chat_id][today]:
            try:
                user = await context.bot.get_chat_member(chat_id, user_id)
                mentions.append(user.user.mention_html())
            except Exception:
                mentions.append(str(user_id))
        msg = "今日已打卡会员：\n" + "\n".join(mentions)
    else:
        msg = "今天还没有会员打卡！"
    await update.message.reply_text(msg, parse_mode="HTML")
