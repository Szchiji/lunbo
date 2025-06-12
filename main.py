import os
import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ChatMemberHandler
)
from plugins.main_menu import show_main_menu, handle_menu_button
from plugins.members import (
    add_member_cmd, remove_member_cmd, list_members_cmd, is_admin, set_admin_ids, get_admin_ids
)
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

import json

# 日志配置
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST")
PORT = int(os.environ.get('PORT', 10000))

if WEBHOOK_HOST:
    WEBHOOK_HOST = WEBHOOK_HOST.rstrip("/")
    WEBHOOK_PATH = f"/bot/{TOKEN}"
    WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
else:
    WEBHOOK_PATH = ""
    WEBHOOK_URL = ""

ADMIN_FILE = "admins.json"

def load_admin_ids():
    try:
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            admin_ids = data.get("admin_ids", [])
            set_admin_ids(admin_ids)
    except Exception:
        set_admin_ids([])

def save_admin_ids():
    admin_ids = get_admin_ids()
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        json.dump({"admin_ids": admin_ids}, f, ensure_ascii=False)

async def start(update, context):
    await update.message.reply_text("欢迎小微机器人！")
    await show_main_menu(update, context)

async def myid(update, context):
    await update.message.reply_text(f"你的用户ID是：{update.effective_user.id}")

async def addadmin(update, context):
    user_id = update.effective_user.id
    args = context.args
    if not is_admin(user_id):
        await update.message.reply_text("只有管理员才能操作。")
        return
    if not args or not args[0].isdigit():
        await update.message.reply_text("请用 /addadmin 用户ID 添加管理员。")
        return
    admin_id = int(args[0])
    ids = get_admin_ids()
    if admin_id not in ids:
        ids.append(admin_id)
        set_admin_ids(ids)
        save_admin_ids()
        await update.message.reply_text(f"已添加管理员 {admin_id}")
    else:
        await update.message.reply_text("该用户已是管理员。")

async def deladmin(update, context):
    user_id = update.effective_user.id
    args = context.args
    if not is_admin(user_id):
        await update.message.reply_text("只有管理员才能操作。")
        return
    if not args or not args[0].isdigit():
        await update.message.reply_text("请用 /deladmin 用户ID 移除管理员。")
        return
    admin_id = int(args[0])
    ids = get_admin_ids()
    if admin_id in ids:
        ids.remove(admin_id)
        set_admin_ids(ids)
        save_admin_ids()
        await update.message.reply_text(f"已移除管理员 {admin_id}")
    else:
        await update.message.reply_text("该用户不是管理员。")

async def list_admins(update, context):
    ids = get_admin_ids()
    if not ids:
        await update.message.reply_text("暂无管理员。")
    else:
        await update.message.reply_text("管理员ID列表：\n" + "\n".join(str(i) for i in ids))

def build_app():
    load_admin_ids()
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
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("deladmin", deladmin))
    app.add_handler(CommandHandler("listadmins", list_admins))
    app.add_handler(ChatMemberHandler(welcome_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), auto_reply_handler))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(), auto_reply_step))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(), schedule_step))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_menu_button))
    return app

if __name__ == "__main__":
    app = build_app()
    import asyncio
    if WEBHOOK_URL:
        asyncio.run(app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL
        ))
    else:
        asyncio.run(app.run_polling())
