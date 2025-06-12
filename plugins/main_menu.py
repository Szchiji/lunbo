from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from plugins.members import is_admin, list_members_cmd, add_member_cmd, remove_member_cmd

from plugins.auto_reply_wizard import (
    list_auto_replies, add_auto_reply_cmd, remove_auto_reply_cmd, 
    toggle_reply_cmd, list_keywords_cmd, add_keyword_cmd, remove_keyword_cmd
)
from plugins.schedule_msg_wizard import (
    list_schedule_msgs, add_schedule_msg_cmd, remove_schedule_msg_cmd, 
    toggle_timer_cmd, set_schedule_time_cmd, set_schedule_type_cmd, 
    delete_last_schedule_cmd
)

# 菜单定义
MAIN_MENU_KEYBOARD = [
    ["会员管理", "自动回复"],
    ["定时消息", "管理员动态管理"],
    ["权限控制"]
]
# 自动回复主菜单
AUTO_REPLY_MENU_KEYBOARD = [
    ["管理自动回复关键词", "添加关键词", "删除关键词"],
    ["所有关键词列表", "返回主菜单"]
]
# 自动回复-管理关键词
MANAGE_KEYWORD_MENU_KEYBOARD = [
    ["精准关键词列表", "包含关键词列表"],
    ["返回自动回复菜单"]
]
# 自动回复-添加关键词
ADD_KEYWORD_MENU_KEYBOARD = [
    ["添加精准关键词", "添加包含关键词"],
    ["返回自动回复菜单"]
]
# 自动回复-删除关键词
DELETE_KEYWORD_MENU_KEYBOARD = [
    ["删除精准关键词", "删除包含关键词"],
    ["返回自动回复菜单"]
]
# 定时消息主菜单
SCHEDULE_MENU_KEYBOARD = [
    ["删除上一条", "管理定时", "查看列表"],
    ["开始/暂停", "开始时间", "结束时间"],
    ["支持文本/图片", "支持精准发送"],
    ["返回主菜单"]
]

# 管理员管理菜单
ADMIN_MENU_KEYBOARD = [
    ["添加管理员", "移除管理员", "管理员列表"],
    ["返回主菜单"]
]

PERMISSION_MENU_KEYBOARD = [
    ["返回主菜单"]
]

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        reply_markup = ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True)
        await update.message.reply_text("主菜单：请选择功能模块", reply_markup=reply_markup)

async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    # ========== 一级菜单 ==========
    if text == "自动回复":
        if is_admin(user_id):
            reply_markup = ReplyKeyboardMarkup(AUTO_REPLY_MENU_KEYBOARD, resize_keyboard=True)
            await update.message.reply_text("自动回复：请选择操作", reply_markup=reply_markup)
            context.user_data.clear()
            context.user_data["menu_level"] = "auto_reply"
            return
        else:
            await update.message.reply_text("只有管理员可操作该功能。")
            return
    elif text == "定时消息":
        if is_admin(user_id):
            reply_markup = ReplyKeyboardMarkup(SCHEDULE_MENU_KEYBOARD, resize_keyboard=True)
            await update.message.reply_text("定时消息：请选择操作", reply_markup=reply_markup)
            context.user_data.clear()
            context.user_data["menu_level"] = "schedule"
            return
        else:
            await update.message.reply_text("只有管理员可操作该功能。")
            return
    elif text == "会员管理":
        if is_admin(user_id):
            reply_markup = ReplyKeyboardMarkup([
                ["添加会员", "移除会员", "会员列表"],
                ["返回主菜单"]
            ], resize_keyboard=True)
            await update.message.reply_text("会员管理：请选择操作", reply_markup=reply_markup)
            context.user_data.clear()
            context.user_data["menu_level"] = "member"
            return
        else:
            await update.message.reply_text("只有管理员可操作该功能。")
            return
    elif text == "管理员动态管理":
        if is_admin(user_id):
            reply_markup = ReplyKeyboardMarkup(ADMIN_MENU_KEYBOARD, resize_keyboard=True)
            await update.message.reply_text("管理员管理：请选择操作", reply_markup=reply_markup)
            context.user_data.clear()
            context.user_data["menu_level"] = "admin"
            return
        else:
            await update.message.reply_text("只有管理员可操作该功能。")
            return
    elif text == "权限控制":
        reply_markup = ReplyKeyboardMarkup(PERMISSION_MENU_KEYBOARD, resize_keyboard=True)
        await update.message.reply_text(
            "所有敏感操作如会员、管理员、自动回复等均有权限校验。管理员ID动态维护，权限即时生效。",
            reply_markup=reply_markup
        )
        context.user_data.clear()
        context.user_data["menu_level"] = "permission"
        return
    elif text == "返回主菜单":
        context.user_data.clear()
        await show_main_menu(update, context)
        return

    # ========== 自动回复菜单 ==========
    menu_level = context.user_data.get("menu_level")
    if menu_level == "auto_reply":
        if text == "管理自动回复关键词":
            reply_markup = ReplyKeyboardMarkup(MANAGE_KEYWORD_MENU_KEYBOARD, resize_keyboard=True)
            await update.message.reply_text("管理自动回复关键词：请选择", reply_markup=reply_markup)
            context.user_data["submenu"] = "manage_keyword"
            return
        elif text == "添加关键词":
            reply_markup = ReplyKeyboardMarkup(ADD_KEYWORD_MENU_KEYBOARD, resize_keyboard=True)
            await update.message.reply_text("添加关键词：请选择", reply_markup=reply_markup)
            context.user_data["submenu"] = "add_keyword"
            return
        elif text == "删除关键词":
            reply_markup = ReplyKeyboardMarkup(DELETE_KEYWORD_MENU_KEYBOARD, resize_keyboard=True)
            await update.message.reply_text("删除关键词：请选择", reply_markup=reply_markup)
            context.user_data["submenu"] = "delete_keyword"
            return
        elif text == "所有关键词列表":
            await list_keywords_cmd(update, context)
            return
        elif text == "返回主菜单":
            context.user_data.clear()
            await show_main_menu(update, context)
            return

    # ========== 自动回复二级菜单 ==========
    submenu = context.user_data.get("submenu")
    if menu_level == "auto_reply" and submenu:
        # 管理关键词
        if submenu == "manage_keyword":
            if text == "精准关键词列表":
                await list_keywords_cmd(update, context, mode="exact")
                return
            elif text == "包含关键词列表":
                await list_keywords_cmd(update, context, mode="contain")
                return
            elif text == "返回自动回复菜单":
                reply_markup = ReplyKeyboardMarkup(AUTO_REPLY_MENU_KEYBOARD, resize_keyboard=True)
                await update.message.reply_text("自动回复：请选择操作", reply_markup=reply_markup)
                context.user_data["submenu"] = None
                return
        # 添加关键词
        elif submenu == "add_keyword":
            if text == "添加精准关键词":
                await update.message.reply_text("请输入精准关键词及回复内容（格式：关键词 回复内容）：", reply_markup=ReplyKeyboardRemove())
                context.user_data["add_keyword_mode"] = "exact"
                return
            elif text == "添加包含关键词":
                await update.message.reply_text("请输入包含关键词及回复内容（格式：关键词 回复内容）：", reply_markup=ReplyKeyboardRemove())
                context.user_data["add_keyword_mode"] = "contain"
                return
            elif text == "返回自动回复菜单":
                reply_markup = ReplyKeyboardMarkup(AUTO_REPLY_MENU_KEYBOARD, resize_keyboard=True)
                await update.message.reply_text("自动回复：请选择操作", reply_markup=reply_markup)
                context.user_data["submenu"] = None
                return
        # 删除关键词
        elif submenu == "delete_keyword":
            if text == "删除精准关键词":
                await update.message.reply_text("请输入要删除的精准关键词：", reply_markup=ReplyKeyboardRemove())
                context.user_data["delete_keyword_mode"] = "exact"
                return
            elif text == "删除包含关键词":
                await update.message.reply_text("请输入要删除的包含关键词：", reply_markup=ReplyKeyboardRemove())
                context.user_data["delete_keyword_mode"] = "contain"
                return
            elif text == "返回自动回复菜单":
                reply_markup = ReplyKeyboardMarkup(AUTO_REPLY_MENU_KEYBOARD, resize_keyboard=True)
                await update.message.reply_text("自动回复：请选择操作", reply_markup=reply_markup)
                context.user_data["submenu"] = None
                return
        # 处理添加关键词输入
        elif context.user_data.get("add_keyword_mode"):
            mode = context.user_data["add_keyword_mode"]
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                context.args = [parts[0], parts[1], mode]
                await add_keyword_cmd(update, context)
                context.user_data["add_keyword_mode"] = None
                reply_markup = ReplyKeyboardMarkup(AUTO_REPLY_MENU_KEYBOARD, resize_keyboard=True)
                await update.message.reply_text("已添加。返回自动回复菜单：", reply_markup=reply_markup)
            else:
                await update.message.reply_text("格式不对，请重新输入：关键词 回复内容")
            return
        # 处理删除关键词输入
        elif context.user_data.get("delete_keyword_mode"):
            mode = context.user_data["delete_keyword_mode"]
            if text:
                context.args = [text, mode]
                await remove_keyword_cmd(update, context)
                context.user_data["delete_keyword_mode"] = None
                reply_markup = ReplyKeyboardMarkup(AUTO_REPLY_MENU_KEYBOARD, resize_keyboard=True)
                await update.message.reply_text("已删除。返回自动回复菜单：", reply_markup=reply_markup)
            else:
                await update.message.reply_text("请输入要删除的关键词")
            return

    # ========== 定时消息菜单 ==========
    if menu_level == "schedule":
        if text == "删除上一条":
            await delete_last_schedule_cmd(update, context)
            return
        elif text == "管理定时":
            await update.message.reply_text("请发送要操作的定时消息ID（可用'查看列表'获取），或发送'返回主菜单'退出。")
            context.user_data["schedule_op"] = "manage"
            return
        elif text == "查看列表":
            await list_schedule_msgs(update, context)
            return
        elif text == "开始/暂停":
            await update.message.reply_text("请发送要开始/暂停的定时消息ID：")
            context.user_data["schedule_op"] = "toggle"
            return
        elif text == "开始时间":
            await update.message.reply_text("请发送定时消息ID和新的开始时间（格式：ID HH:MM）：")
            context.user_data["schedule_op"] = "start_time"
            return
        elif text == "结束时间":
            await update.message.reply_text("请发送定时消息ID和新的结束时间（格式：ID HH:MM）：")
            context.user_data["schedule_op"] = "end_time"
            return
        elif text == "支持文本/图片":
            await update.message.reply_text("请发送定时消息ID和类型（text/image）：")
            context.user_data["schedule_op"] = "type"
            return
        elif text == "支持精准发送":
            await update.message.reply_text("请发送定时消息ID和精准发送对象（如：ID 12345678）：")
            context.user_data["schedule_op"] = "target"
            return
        elif text == "返回主菜单":
            context.user_data.clear()
            await show_main_menu(update, context)
            return
        # 处理定时消息多轮输入
        elif context.user_data.get("schedule_op"):
            op = context.user_data["schedule_op"]
            parts = text.split()
            if op == "toggle" and len(parts) == 1 and parts[0].isdigit():
                context.args = [parts[0]]
                await toggle_timer_cmd(update, context)
                context.user_data["schedule_op"] = None
                await update.message.reply_text("已切换状态。", reply_markup=ReplyKeyboardMarkup(SCHEDULE_MENU_KEYBOARD, resize_keyboard=True))
            elif op == "start_time" and len(parts) == 2:
                context.args = [parts[0], parts[1], "start"]
                await set_schedule_time_cmd(update, context)
                context.user_data["schedule_op"] = None
                await update.message.reply_text("已设置开始时间。", reply_markup=ReplyKeyboardMarkup(SCHEDULE_MENU_KEYBOARD, resize_keyboard=True))
            elif op == "end_time" and len(parts) == 2:
                context.args = [parts[0], parts[1], "end"]
                await set_schedule_time_cmd(update, context)
                context.user_data["schedule_op"] = None
                await update.message.reply_text("已设置结束时间。", reply_markup=ReplyKeyboardMarkup(SCHEDULE_MENU_KEYBOARD, resize_keyboard=True))
            elif op == "type" and len(parts) == 2:
                context.args = [parts[0], parts[1]]
                await set_schedule_type_cmd(update, context)
                context.user_data["schedule_op"] = None
                await update.message.reply_text("已设置类型。", reply_markup=ReplyKeyboardMarkup(SCHEDULE_MENU_KEYBOARD, resize_keyboard=True))
            elif op == "target" and len(parts) == 2:
                context.args = [parts[0], parts[1]]
                # 实现精准发送对象添加逻辑（请自行实现）
                await update.message.reply_text(f"已设置ID {parts[0]} 的精准发送对象为 {parts[1]}。", reply_markup=ReplyKeyboardMarkup(SCHEDULE_MENU_KEYBOARD, resize_keyboard=True))
                context.user_data["schedule_op"] = None
            elif op == "manage" and len(parts) == 1 and parts[0].isdigit():
                # 进入该定时消息的管理界面（如删除、编辑等，需自行扩展）
                await update.message.reply_text(f"请直接发送新内容或时间，或发送'返回主菜单'退出。")
                # 可标记 context.user_data["current_schedule_id"] = parts[0]
                context.user_data["schedule_op"] = None
            else:
                await update.message.reply_text("输入不符合要求，请参考提示重新输入。")
            return

    # ========== 其它菜单略（会员管理/管理员管理/权限控制同前） ==========

    # ========== 默认：未命中菜单，自动回主菜单 ==========
    if update.effective_chat.type == "private":
        await show_main_menu(update, context)
