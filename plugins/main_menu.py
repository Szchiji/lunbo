from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

MAIN_MENU = [
    ["我要打卡", "查看今日打卡会员"],
    ["帮助", "关于机器人"]
]
ADMIN_MENU = [
    ["会员管理", "自动回复管理"],
    ["定时消息管理", "返回主菜单"]
]
MEMBER_MGR_MENU = [
    ["添加会员", "移除会员", "会员列表"],
    ["返回管理员菜单"]
]
AUTO_REPLY_MGR_MENU = [
    ["添加自动回复", "管理自动回复"],
    ["返回管理员菜单"]
]
SCHEDULE_MGR_MENU = [
    ["添加定时消息", "管理定时消息"],
    ["返回管理员菜单"]
]

def is_admin_member(member):
    return member.status in ("administrator", "creator")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await update.effective_chat.get_member(update.effective_user.id)
    menu = MAIN_MENU.copy()
    if is_admin_member(member):
        menu = [*MAIN_MENU, ["管理员设置"]]
    markup = ReplyKeyboardMarkup(menu, resize_keyboard=True)
    await update.message.reply_text("请选择操作：", reply_markup=markup)

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup(ADMIN_MENU, resize_keyboard=True)
    await update.message.reply_text("管理员设置菜单：", reply_markup=markup)

async def show_member_mgr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup(MEMBER_MGR_MENU, resize_keyboard=True)
    await update.message.reply_text("会员管理：", reply_markup=markup)

async def show_auto_reply_mgr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup(AUTO_REPLY_MGR_MENU, resize_keyboard=True)
    await update.message.reply_text("自动回复管理：", reply_markup=markup)

async def show_schedule_mgr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup(SCHEDULE_MGR_MENU, resize_keyboard=True)
    await update.message.reply_text("定时消息管理：", reply_markup=markup)

async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    member = await update.effective_chat.get_member(update.effective_user.id)
    is_admin = is_admin_member(member)
    # 主菜单
    if text == "我要打卡":
        from .checkin import checkin
        await checkin(update, context)
    elif text == "查看今日打卡会员":
        from .checkin import checkin_stats
        await checkin_stats(update, context)
    elif text == "帮助":
        await update.message.reply_text("可用命令和说明：/menu /start")
    elif text == "关于机器人":
        await update.message.reply_text("小微群机器人，支持多群、会员、定制消息、打卡、定时消息、自动回复、按钮等。")
    # 管理员菜单
    elif is_admin:
        if text == "管理员设置":
            await show_admin_menu(update, context)
        elif text == "返回主菜单":
            await show_main_menu(update, context)
        elif text == "会员管理":
            await show_member_mgr(update, context)
        elif text == "自动回复管理":
            await show_auto_reply_mgr(update, context)
        elif text == "定时消息管理":
            await show_schedule_mgr(update, context)
        elif text == "返回管理员菜单":
            await show_admin_menu(update, context)
        elif text == "添加会员":
            await update.message.reply_text("请发送：/add_member 用户ID 天数(0=永久)")
        elif text == "移除会员":
            await update.message.reply_text("请发送：/remove_member 用户ID")
        elif text == "会员列表":
            from .members import list_members_cmd
            await list_members_cmd(update, context)
        elif text == "添加自动回复":
            from .auto_reply_wizard import auto_reply_entry
            await auto_reply_entry(update, context)
        elif text == "管理自动回复":
            from .auto_reply_wizard import list_auto_replies
            await list_auto_replies(update, context)
        elif text == "添加定时消息":
            from .schedule_msg_wizard import schedule_entry
            await schedule_entry(update, context)
        elif text == "管理定时消息":
            from .schedule_msg_wizard import list_schedule_msgs
            await list_schedule_msgs(update, context)
        else:
            await update.message.reply_text("暂不支持该操作。")
    else:
        await update.message.reply_text("暂不支持该操作。")
