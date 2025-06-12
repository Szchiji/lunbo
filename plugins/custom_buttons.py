from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def send_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("我要打卡", callback_data="checkin")],
        [InlineKeyboardButton("查看今日打卡会员", callback_data="checkin_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👇请选择操作：", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "checkin":
        from .checkin import checkin
        await checkin(update, context)
    elif query.data == "checkin_stats":
        from .checkin import checkin_stats
        await checkin_stats(update, context)
