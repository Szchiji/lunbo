import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
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

# --------------------- 取消流程实现 ---------------------

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """对话流程中 用户输入 /cancel 的处理函数"""
    if update.message:
        await update.message.reply_text("已取消操作。")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("已取消操作。")
    return ConversationHandler.END

async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """对话流程中 用户点击“取消”按钮的处理函数"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("已取消操作。")
    return ConversationHandler.END

def cancel_keyboard():
    """返回带取消按钮的 InlineKeyboard"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ 取消", callback_data="cancel")]])

# --------------------- 各步骤包装带取消按钮 ---------------------
# 下面以 add_text 为例，edit_xxx 类似
async def add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "请输入定时消息的文本内容，或点击取消。",
        reply_markup=cancel_keyboard()
    )
    # ...其余逻辑

# add_media、add_button...等步骤都建议在 reply_markup 里加 cancel_keyboard()

# --------------------- 主入口 ---------------------

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
