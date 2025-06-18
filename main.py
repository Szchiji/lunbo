import logging
import os
import asyncio
import datetime
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
)
from config import BOT_TOKEN, WEBHOOK_URL, GROUPS
from db import init_db, fetch_schedules
from modules.scheduler import (
    show_schedule_list, entry_add_schedule, confirm_callback,
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
from modules.keyboards import schedule_list_menu, group_feature_menu, group_select_menu
from modules.keywords_reply import (
    keywords_setting_entry, kw_add_start, kw_add_receive, kw_remove, kw_remove_confirm, kw_enable, kw_enable_confirm,
    kw_disable, kw_disable_confirm, kw_delay, kw_delayset_confirm, kw_back, keyword_autoreply,
    kw_edit, kw_edit_entry, kw_edit_save
)
from telegram.error import BadRequest

logging.basicConfig(level=logging.INFO)

async def start(update, context):
    await update.message.reply_text(
        "欢迎使用定时消息管理 Bot，可发送 /schedule 查看和编辑定时消息。\n发送 /keyword 可管理关键词自动回复。"
    )

async def schedule_entry(update, context):
    await update.message.reply_text("请选择群聊：", reply_markup=group_select_menu(GROUPS))

async def select_group_callback(update, context):
    query = update.callback_query
    group_id = int(query.data.replace("set_group_", ""))
    context.user_data["selected_group_id"] = group_id
    group_name = GROUPS.get(group_id, str(group_id))
    await query.edit_message_text(
        f"已选择群聊：{group_name}\n请选择要管理的功能：",
        reply_markup=group_feature_menu(group_id, group_name=group_name)
    )

async def group_keywords_entry(update, context):
    query = update.callback_query
    group_id = int(query.data.replace("group_", "").replace("_keywords", ""))
    context.user_data["selected_group_id"] = group_id
    await keywords_setting_entry(update, context)

async def group_schedule_entry(update, context):
    query = update.callback_query
    group_id = int(query.data.replace("group_", "").replace("_schedule", ""))
    context.user_data["selected_group_id"] = group_id
    schedules = await fetch_schedules(group_id)
    group_name = GROUPS.get(group_id) or str(group_id)
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    await query.edit_message_text(
        f"⏰【{group_name} 定时消息管理】\n时间：{now_str}\n（此页可管理所有定时消息）",
        reply_markup=schedule_list_menu(schedules, group_name=group_name)
    )

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
        reply_markup=schedule_list_menu(schedules, group_name=group_name)
    )
    return ConversationHandler.END

async def back_to_menu_callback(update, context):
    group_id = context.user_data.get("selected_group_id") or update.effective_chat.id
    schedules = await fetch_schedules(group_id)
    group_name = GROUPS.get(group_id) or str(group_id)
    await update.callback_query.edit_message_text(
        f"⏰ [{group_name}] 定时消息列表：\n点击条目可设置。",
        reply_markup=schedule_list_menu(schedules, group_name=group_name)
    )
    return ConversationHandler.END

async def back_to_prev_callback(update, context):
    group_id = context.user_data.get("selected_group_id")
    group_name = GROUPS.get(group_id, str(group_id))
    await update.callback_query.edit_message_text(
        f"已选择群聊：{group_name}\n请选择要管理的功能：\n\n操作时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        reply_markup=group_feature_menu(group_id, group_name=group_name)
    )

async def main_menu_callback(update, context):
    await update.callback_query.edit_message_text(
        "请选择群聊：\n\n操作时间：{}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        reply_markup=group_select_menu(GROUPS)
    )

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schedule", schedule_entry))

    # 群聊选择和功能菜单
    application.add_handler(CallbackQueryHandler(select_group_callback, pattern="^set_group_"))
    application.add_handler(CallbackQueryHandler(group_keywords_entry, pattern=r"^group_-?\d+_keywords$"))
    application.add_handler(CallbackQueryHandler(group_schedule_entry, pattern=r"^group_-?\d+_schedule$"))
    application.add_handler(CallbackQueryHandler(back_to_prev_callback, pattern="^back_to_prev$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))

    # 关键词自动回复相关（仅用正则或命令，不用全局文本 handler！）
    application.add_handler(CommandHandler("keyword", keywords_setting_entry))
    application.add_handler(MessageHandler(filters.Regex(r"^/?关键词$"), keywords_setting_entry))
    application.add_handler(CallbackQueryHandler(keywords_setting_entry, pattern="^kw_back$"))
    application.add_handler(CallbackQueryHandler(kw_add_start, pattern="^kw_add$"))
    application.add_handler(CallbackQueryHandler(kw_remove, pattern="^kw_remove$"))
    application.add_handler(CallbackQueryHandler(kw_remove_confirm, pattern=r"^kw_remove_"))
    application.add_handler(CallbackQueryHandler(kw_enable, pattern="^kw_enable$"))
    application.add_handler(CallbackQueryHandler(kw_enable_confirm, pattern=r"^kw_enable_"))
    application.add_handler(CallbackQueryHandler(kw_disable, pattern="^kw_disable$"))
    application.add_handler(CallbackQueryHandler(kw_disable_confirm, pattern=r"^kw_disable_"))
    application.add_handler(CallbackQueryHandler(kw_delay, pattern=r"^kw_delay_\d+$"))
    application.add_handler(CallbackQueryHandler(kw_delayset_confirm, pattern=r"^kw_delayset_"))
    application.add_handler(CallbackQueryHandler(kw_edit, pattern="^kw_edit$"))
    application.add_handler(CallbackQueryHandler(kw_edit_entry, pattern=r"^kw_edit_"))
    # 不要全局 MessageHandler(filters.TEXT...)

    # ConversationHandler：定时消息多步流程（只有多步相关入口！）
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(entry_add_schedule, pattern="^add_schedule$"),
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
            CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"),
        ],
        states={
            SELECT_GROUP: [
                CallbackQueryHandler(select_group_callback, pattern="^set_group_"),
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
                CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$")
            ],
            EDIT_MEDIA: [
                MessageHandler((filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.TEXT) & (~filters.COMMAND), edit_media_save),
                CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$")
            ],
            EDIT_BUTTON: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_button_save),
                CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$")
            ],
            EDIT_REPEAT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_repeat_save),
                CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$")
            ],
            EDIT_PERIOD: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_period_save),
                CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$")
            ],
            EDIT_START_DATE: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_start_date_save),
                CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$")
            ],
            EDIT_END_DATE: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), edit_end_date_save),
                CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$")
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel_callback, pattern="^cancel$"),
        ],
        allow_reentry=True
    )
    application.add_handler(conv)

    async def on_startup(app):
        await init_db()
        app.bot_data["GROUPS"] = GROUPS
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

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    bg_task = None
    main()
