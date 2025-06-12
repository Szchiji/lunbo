import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)
from config import BOT_TOKEN, WEBHOOK_URL, GROUP_IDS
from db import init_db
from modules.scheduler import (
    show_schedule_list, callback_query_handler,
    edit_text, edit_media, edit_button, edit_repeat, edit_period, edit_start_date, edit_end_date,
    EDIT_TEXT, EDIT_MEDIA, EDIT_BUTTON, EDIT_REPEAT, EDIT_PERIOD, EDIT_DATE
)
from modules.broadcast import schedule_broadcast_jobs

logging.basicConfig(level=logging.INFO)

async def start(update, context):
    await update.message.reply_text("欢迎使用群定时消息机器人！\n请用 /schedule 管理定时消息。")

async def schedule(update, context):
    await show_schedule_list(update, context)

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).webhook_url(WEBHOOK_URL).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schedule", schedule))
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    conv = ConversationHandler(
        entry_points=[],
        states={
            EDIT_TEXT: [MessageHandler(filters.TEXT, edit_text)],
            EDIT_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO | filters.TEXT, edit_media)],
            EDIT_BUTTON: [MessageHandler(filters.TEXT, edit_button)],
            EDIT_REPEAT: [MessageHandler(filters.TEXT, edit_repeat)],
            EDIT_PERIOD: [MessageHandler(filters.TEXT, edit_period)],
            EDIT_DATE: [MessageHandler(filters.TEXT, edit_start_date)],
            EDIT_DATE + 1: [MessageHandler(filters.TEXT, edit_end_date)],
        },
        fallbacks=[],
        map_to_parent={ConversationHandler.END: ConversationHandler.END},
    )
    application.add_handler(conv)

    async def on_startup(app):
        await init_db()
        logging.info("数据库初始化完成")
        schedule_broadcast_jobs(application, GROUP_IDS)

    application.post_init = on_startup
    application.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()
