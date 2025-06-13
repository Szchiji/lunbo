import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
)
from config import BOT_TOKEN, WEBHOOK_URL, GROUP_IDS
from db import init_db
from modules.scheduler import (
    show_schedule_list, callback_query_handler,
    edit_text, edit_media, edit_button, edit_repeat, edit_period, edit_start_date, edit_end_date,
    add_text, add_media, add_button, add_repeat, add_period, add_start_date, add_end_date, add_confirm,
    ADD_TEXT, ADD_MEDIA, ADD_BUTTON, ADD_REPEAT, ADD_PERIOD, ADD_START_DATE, ADD_END_DATE, ADD_CONFIRM,
    EDIT_TEXT, EDIT_MEDIA, EDIT_BUTTON, EDIT_REPEAT, EDIT_PERIOD, EDIT_DATE
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
        entry_points=[CallbackQueryHandler(callback_query_handler)],
        states={
            # 编辑流程
            EDIT_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_text),
                        CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            EDIT_MEDIA: [MessageHandler((filters.PHOTO | filters.VIDEO | filters.TEXT) & (~filters.COMMAND), edit_media),
                         CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            EDIT_BUTTON: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_button),
                          CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            EDIT_REPEAT: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_repeat),
                          CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            EDIT_PERIOD: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_period),
                          CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            EDIT_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_start_date),
                        CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            EDIT_DATE + 1: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_end_date),
                            CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            # 添加流程
            ADD_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_text),
                       CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            ADD_MEDIA: [MessageHandler((filters.PHOTO | filters.VIDEO | filters.TEXT) & (~filters.COMMAND), add_media),
                        CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            ADD_BUTTON: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_button),
                         CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            ADD_REPEAT: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_repeat),
                         CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            ADD_PERIOD: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_period),
                         CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            ADD_START_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_start_date),
                             CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            ADD_END_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_end_date),
                           CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            ADD_CONFIRM: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_confirm),
                          CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
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
        schedule_broadcast_jobs(app, GROUP_IDS)

    application.post_init = on_startup
    application.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()
