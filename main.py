import logging
import os
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ChatMemberHandler
)
from plugins.main_menu import (
    show_main_menu, handle_menu_button, show_admin_menu, show_member_mgr,
    show_auto_reply_mgr, show_schedule_mgr
)
from plugins.members import add_member_cmd, remove_member_cmd, list_members_cmd
from plugins.auto_reply_wizard import (
    auto_reply_entry, auto_reply_step, auto_reply_media_choice,
    list_auto_replies, toggle_reply_cmd, del_reply_cmd, auto_reply_handler
)
from plugins.schedule_msg_wizard import (
    schedule_entry, schedule_step, schedule_media_choice,
    list_schedule_msgs, toggle_timer_cmd, del_timer_cmd
)
from plugins.checkin import checkin, checkin_stats
from plugins.custom_buttons import send_button, button_callback
from plugins.welcome import welcome_handler

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text("欢迎使用小微机器人！")
    await show_main_menu(update, context)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", show_main_menu))
app.add_handler(CommandHandler("add_member", add_member_cmd))
app.add_handler(CommandHandler("remove_member", remove_member_cmd))
app.add_handler(CommandHandler("list_members", list_members_cmd))
app.add_handler(CommandHandler("toggle_reply", toggle_reply_cmd))
app.add_handler(CommandHandler("del_reply", del_reply_cmd))
app.add_handler(CommandHandler("toggle_timer", toggle_timer_cmd))
app.add_handler(CommandHandler("del_timer", del_timer_cmd))
app.add_handler(CommandHandler("button", send_button))
app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(CallbackQueryHandler(auto_reply_media_choice, pattern="^ar_media_"))
app.add_handler(CallbackQueryHandler(schedule_media_choice, pattern="^sch_media_"))
app.add_handler(CommandHandler("checkin", checkin))
app.add_handler(CommandHandler("checkin_stats", checkin_stats))
app.add_handler(ChatMemberHandler(welcome_handler, ChatMemberHandler.CHAT_MEMBER))
# 多轮自动回复和定时消息设置
app.add_handler(MessageHandler(filters.TEXT & filters.User(), auto_reply_step))
app.add_handler(MessageHandler(filters.TEXT & filters.User(), schedule_step))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_menu_button))
# 自动回复触发
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), auto_reply_handler))

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_polling())
