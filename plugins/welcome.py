from telegram.ext import ContextTypes

async def welcome_handler(update, context: ContextTypes.DEFAULT_TYPE):
    if update.chat_member.difference().get("status") == "member":
        user = update.chat_member.new_chat_member.user.mention_html()
        msg = f"欢迎 {user} 加入本群！"
        await context.bot.send_message(
            chat_id=update.chat_member.chat.id,
            text=msg,
            parse_mode="HTML"
        )
