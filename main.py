import os
import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ChatMemberHandler
)
# 这里假设你有以下自定义插件，可根据你的目录结构调整
from plugins.main_menu import show_main_menu, handle_menu_button
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

# 日志配置
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST")  # 如 https://xxx.onrender.com（Webhook模式用）
WEBHOOK_PATH = f"/bot/{TOKEN}" if WEBHOOK_HOST else ""
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""
PORT = int(os.environ.get('PORT', 10000))

# /start 指令
async def start(update, context):
    await update.message.reply_text("欢迎使用机器人！")
    await show_main_menu(update, context)

def build_app():
    # Webhook模式
    if WEBHOOK_HOST:
        app = ApplicationBuilder().token(TOKEN).webhook_url(WEBHOOK_URL).build()
    else:
        app = ApplicationBuilder().token(TOKEN).build()

    # 指令与处理器注册
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
    return app

if __name__ == "__main__":
    app = build_app()
    import asyncio
    if WEBHOOK_HOST:
        # Webhook模式（用于Render Web Service等）
        asyncio.run(app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
        ))
    else:
        # 轮询模式（本地开发或后台Worker）
        asyncio.run(app.run_polling())
