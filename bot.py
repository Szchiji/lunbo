import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
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
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schedule", schedule))

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(callback_query_handler)],
        states={
            EDIT_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_text)],
            EDIT_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO | filters.TEXT, edit_media)],
            EDIT_BUTTON: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_button)],
            EDIT_REPEAT: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_repeat)],
            EDIT_PERIOD: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_period)],
            EDIT_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_start_date)],
            EDIT_DATE + 1: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_end_date)],
        },
        fallbacks=[],
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
