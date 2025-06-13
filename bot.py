import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
)
from config import BOT_TOKEN, WEBHOOK_URL, GROUP_IDS
from db import init_db
from modules.scheduler import (
    show_schedule_list, entry_add_schedule, select_group_callback, confirm_callback,
    edit_text, edit_media, edit_button, edit_repeat, add_period, add_start_date, add_end_date, add_confirm,
    add_text, add_media, add_button, add_repeat, add_period, add_start_date, add_end_date, add_confirm,
    SELECT_GROUP, ADD_TEXT, ADD_MEDIA, ADD_BUTTON, ADD_REPEAT, ADD_PERIOD, ADD_START_DATE, ADD_END_DATE, ADD_CONFIRM
)
from modules.broadcast import schedule_broadcast_jobs

logging.basicConfig(level=logging.INFO)

async def start(update, context):
    await update.message.reply_text("欢迎使用群定时消息机器人！\n请用 /schedule 管理定时消息。")

async def schedule(update, context):
    await show_schedule_list(update, context)

async def cancel(update, context):
    if update.message:
        await update.message.reply_text("已取消操作。")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("已取消操作。")
    return ConversationHandler.END

async def cancel_callback(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("已取消操作。")
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schedule", schedule))

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("schedule", schedule),
            MessageHandler(filters.Regex("^添加定时消息$"), entry_add_schedule)
        ],
        states={
            SELECT_GROUP: [CallbackQueryHandler(select_group_callback)],
            ADD_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_text)],
            ADD_MEDIA: [MessageHandler((filters.PHOTO | filters.VIDEO | filters.TEXT) & (~filters.COMMAND), add_media)],
            ADD_BUTTON: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_button)],
            ADD_REPEAT: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_repeat)],
            ADD_PERIOD: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_period)],
            ADD_START_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_start_date)],
            ADD_END_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_end_date)],
            ADD_CONFIRM: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), add_confirm),
                CallbackQueryHandler(confirm_callback)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel_callback, pattern='^cancel$'),
        ],
    )
    application.add_handler(conv)

    async def on_startup(app):
        await init_db()
        logging.info("数据库初始化完成")
        schedule_broadcast_jobs(app)

    application.post_init = on_startup
    application.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()
