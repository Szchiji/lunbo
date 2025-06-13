import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
)
from config import BOT_TOKEN, WEBHOOK_URL, GROUP_IDS
from db import init_db
from modules.scheduler import (
    show_schedule_list, add_text, add_media, add_button, add_repeat, add_period,
    add_start_date, add_end_date, add_confirm,
    ADD_TEXT, ADD_MEDIA, ADD_BUTTON, ADD_REPEAT, ADD_PERIOD, ADD_START_DATE, ADD_END_DATE, ADD_CONFIRM,
    edit_menu, edit_text, save_edit_text, delete_schedule_cb,
    EDIT_MENU, EDIT_TEXT,
    cancel_keyboard,
)
from modules.broadcast import schedule_broadcast_jobs

logging.basicConfig(level=logging.INFO)

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
    application.add_handler(CommandHandler("start", lambda update, ctx: update.message.reply_text("欢迎使用群定时消息机器人！\n用 /schedule 管理定时消息。")))
    application.add_handler(CommandHandler("schedule", show_schedule_list))

    conv = ConversationHandler(
        entry_points=[CommandHandler("schedule", show_schedule_list)],
        states={
            ADD_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_text),
                       CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            ADD_MEDIA: [MessageHandler((filters.PHOTO | filters.VIDEO | filters.TEXT) & (~filters.COMMAND), add_media),
                        CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            ADD_BUTTON: [MessageHandler(filters.TEXT & (~filters.COMMAND) | filters.PHOTO | filters.VIDEO, add_button),
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

            # 编辑流程
            EDIT_MENU: [CallbackQueryHandler(edit_menu, pattern='^edit_'), 
                        CallbackQueryHandler(cancel_callback, pattern='^cancel$'),
                        CallbackQueryHandler(delete_schedule_cb, pattern='^delete_schedule$')],
            EDIT_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), save_edit_text),
                        CallbackQueryHandler(cancel_callback, pattern='^cancel$')],
            # 你可以继续补充其它EDIT_XXX状态
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel_callback, pattern='^cancel$')
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
