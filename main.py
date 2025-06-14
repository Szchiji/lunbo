import logging
import os
import asyncio
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
)
from config import BOT_TOKEN, WEBHOOK_URL, GROUPS
from db import init_db, fetch_schedules
from modules.scheduler import (
    show_schedule_list, entry_add_schedule, select_group_callback, confirm_callback,
    add_text, add_media, add_button, add_repeat, add_period, add_start_date, add_end_date, add_confirm,
    edit_menu_entry,
    edit_text_entry, edit_text_save,
    edit_media_entry, edit_media_save,
    edit_button_entry, edit_button_save,
    edit_repeat_entry, edit_repeat_save,
    edit_period_entry, edit_period_save,
    edit_start_date_entry, edit_start_date_save,
    edit_end_date_entry, edit_end_date_save,
    toggle_status, toggle_remove_last, toggle_pin, delete_schedule_callback,
    SELECT_GROUP, ADD_TEXT, ADD_MEDIA, ADD_BUTTON, ADD_REPEAT, ADD_PERIOD, ADD_START_DATE, ADD_END_DATE, ADD_CONFIRM,
    EDIT_TEXT, EDIT_MEDIA, EDIT_BUTTON, EDIT_REPEAT, EDIT_PERIOD, EDIT_START_DATE, EDIT_END_DATE,
)
from scheduled_sender import scheduled_sender
from modules.keyboards import schedule_list_menu
from telegram.error import BadRequest

logging.basicConfig(level=logging.INFO)

async def start(update, context):
    await update.message.reply_text("欢迎使用定时消息管理 Bot，可发送 /schedule 查看和编辑定时消息。")

async def cancel(update, context):
    if update.message:
        await update.message.reply_text("已取消操作。")
    elif update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text("已取消操作。")
        except BadRequest:
            pass
    return ConversationHandler.END

async def cancel_callback(update, context):
    query = update.callback_query
    try:
        await query.delete_message()
    except Exception:
        try:
            await query.edit_message_text("已取消操作。")
        except Exception:
            pass
    group_id = context.user_data.get("selected_group_id")
    if not group_id and hasattr(query.message.chat, "id"):
        group_id = query.message.chat.id
    schedules = await fetch_schedules(group_id)
    group_name = GROUPS.get(group_id) or str(group_id)
    await query.message.chat.send_message(
        f"⏰ [{group_name}] 定时消息列表：\n点击条目可设置。",
        reply_markup=schedule_list_menu(schedules)
    )
    return ConversationHandler.END

async def back_to_menu_callback(update, context):
    group_id = context.user_data.get("selected_group_id") or update.effective_chat.id
    schedules = await fetch_schedules(group_id)
    group_name = GROUPS.get(group_id) or str(group_id)
    await update.callback_query.edit_message_text(
        f"⏰ [{group_name}] 定时消息列表：\n点击条目可设置。",
        reply_markup=schedule_list_menu(schedules)
    )
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("schedule", show_schedule_list),
            MessageHandler(filters.Regex("^添加定时消息$"), entry_add_schedule),
            CallbackQueryHandler(entry_add_schedule, pattern="^add_schedule$"),
            MessageHandler(filters.Regex("^/schedule$"), show_schedule_list),
            MessageHandler(filters.Regex("^查看定时消息$"), show_schedule_list),
            CallbackQueryHandler(edit_menu_entry, pattern=r"^edit_menu_\d+$"),
            CallbackQueryHandler(edit_text_entry, pattern=r"^edit_text_\d+$"),
            CallbackQueryHandler(edit_media_entry, pattern=r"^edit_media_\d+$"),
            CallbackQueryHandler(edit_button_entry, pattern=r"^edit_button_\d+$"),
            CallbackQueryHandler(edit_repeat_entry, pattern=r"^edit_repeat_\d+$"),
            CallbackQueryHandler(edit_period_entry, pattern=r"^edit_time_period_\d+$"),
            CallbackQueryHandler(edit_start_date_entry, pattern=r"^edit_start_date_\d+$"),
            CallbackQueryHandler(edit_end_date_entry, pattern=r"^edit_end_date_\d+$"),
            CallbackQueryHandler(toggle_status, pattern=r"^toggle_status_\d+$"),
            CallbackQueryHandler(toggle_remove_last, pattern=r"^toggle_remove_last_\d+$"),
            CallbackQueryHandler(toggle_pin, pattern=r"^toggle_pin_\d+$"),
            CallbackQueryHandler(delete_schedule_callback, pattern=r"^delete_\d+$"),
            # 返回按钮
            CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$'),  # <--- 这里匹配 back_to_menu
        ],
        states={
            SELECT_GROUP: [
                CallbackQueryHandler(select_group_callback, pattern="^set_group_")
            ],
            ADD_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_text)],
            ADD_MEDIA: [MessageHandler((filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.TEXT) & (~filters.COMMAND), add_media)],
            ADD_BUTTON: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_button)],
            ADD_REPEAT: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_repeat)],
            ADD_PERIOD: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_period)],
            ADD_START_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_start_date)],
            ADD_END_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_end_date)],
            ADD_CONFIRM: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), add_confirm),
                CallbackQueryHandler(confirm_callback)
            ],
            EDIT_TEXT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_text_save),
                CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')
            ],
            EDIT_MEDIA: [
                MessageHandler((filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.TEXT) & (~filters.COMMAND), edit_media_save),
                CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')
            ],
            EDIT_BUTTON: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_button_save),
                CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')
            ],
            EDIT_REPEAT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_repeat_save),
                CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')
            ],
            EDIT_PERIOD: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_period_save),
                CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')
            ],
            EDIT_START_DATE: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_start_date_save),
                CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')
            ],
            EDIT_END_DATE: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_end_date_save),
                CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel_callback, pattern='^cancel$'),
        ],
        allow_reentry=True
    )
    application.add_handler(conv)

    async def on_startup(app):
        await init_db()
        logging.info("数据库初始化完成")
        global bg_task
        bg_task = asyncio.create_task(
            scheduled_sender(application, list(GROUPS.keys()))
        )

    async def on_shutdown(app):
        global bg_task
        if bg_task:
            bg_task.cancel()
            try:
                await bg_task
            except asyncio.CancelledError:
                pass
        logging.info("后台任务已关闭。")

    application.post_init = on_startup
    application.post_shutdown = on_shutdown

    # 生产环境永远用 webhook！
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    bg_task = None
    main()
