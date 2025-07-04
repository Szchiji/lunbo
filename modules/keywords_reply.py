import asyncio
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes, ConversationHandler
import db

# Conversation states
KW_ADD = 500
KW_EDIT = 501

def build_keywords_text(kws: list, chat_name: str = "") -> str:
    """格式化已添加的关键词列表文本"""
    if not kws:
        kw_list = "[空]"
    else:
        lines = []
        for k in kws:
            prefix = "*" if k.get("fuzzy") else "-"
            status = "✅" if k.get("enabled", True) else "❌"
            delay = k.get("delay", 0)
            lines.append(f"{prefix} {k['keyword']} {status} 延时:{delay}分")
        kw_list = "\n".join(lines)
    return (
        f"已添加的关键词:\n{kw_list}\n"
        "- 表示精准触发\n"
        "* 表示包含触发"
    )

def keyword_setting_menu() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton("状态", callback_data="noop"),
            InlineKeyboardButton("✅启用", callback_data="kw_enable"),
            InlineKeyboardButton("关闭", callback_data="kw_disable"),
        ],
        [
            InlineKeyboardButton("删除消息(分钟) 🗑", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("否", callback_data="kw_delay_0"),
            InlineKeyboardButton("1", callback_data="kw_delay_1"),
            InlineKeyboardButton("5", callback_data="kw_delay_5"),
            InlineKeyboardButton("10", callback_data="kw_delay_10"),
            InlineKeyboardButton("30", callback_data="kw_delay_30"),
        ],
        [
            InlineKeyboardButton("👍🏻添加", callback_data="kw_add"),
            InlineKeyboardButton("🗑删除", callback_data="kw_remove"),
            InlineKeyboardButton("✏️编辑", callback_data="kw_edit"),
        ],
        [
            InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
            InlineKeyboardButton("主菜单", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(kb)

def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """从上下文或 update 获取当前聊天 ID"""
    if data := context.user_data.get("selected_group_id"):
        return data
    if update.effective_chat:
        return update.effective_chat.id
    return update.effective_user.id

def get_chat_name(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> str:
    return context.bot_data.get("GROUPS", {}).get(chat_id, str(chat_id))

async def keywords_setting_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """关键词管理首页"""
    chat_id = get_chat_id(update, context)
    chat_name = get_chat_name(context, chat_id)
    kws = await db.fetch_keywords(chat_id)
    now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"📝【{chat_name} 关键词管理】\n时间：{now}\n（此页可管理关键词自动回复）"
    text = f"{header}\n\n{build_keywords_text(kws, chat_name)}"
    markup = keyword_setting_menu()

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)

async def kw_add_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """进入添加关键词对话"""
    context.user_data["kw_add_step"] = "keyword"
    buttons = [
        [
            InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
            InlineKeyboardButton("主菜单", callback_data="main_menu"),
        ]
    ]
    await update.callback_query.edit_message_text(
        "【关键词管理 - 添加】\n请输入新关键词（前缀*为模糊匹配，如“*你好”）：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return KW_ADD

async def kw_add_receive(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """接收添加关键词及回复内容"""
    chat_id = get_chat_id(update, context)
    step = context.user_data.get("kw_add_step")

    # 第一步：输入关键词
    if step == "keyword":
        kw = update.message.text.strip()
        if not kw:
            await update.message.reply_text("关键词不能为空，请重新输入：")
            return KW_ADD
        context.user_data["kw_new_keyword"] = kw
        context.user_data["kw_add_step"] = "reply"
        buttons = [
            [
                InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
                InlineKeyboardButton("主菜单", callback_data="main_menu"),
            ]
        ]
        await update.message.reply_text(
            "请输入该关键词的自动回复内容：",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return KW_ADD

    # 第二步：输入回复内容
    kw = context.user_data.get("kw_new_keyword", "")
    reply = update.message.text.strip()
    if not reply:
        await update.message.reply_text("回复内容不能为空，请重新输入：")
        return KW_ADD

    fuzzy = 1 if kw.startswith("*") else 0
    keyword = kw.lstrip("*")
    await db.add_keyword(chat_id, keyword, reply, fuzzy, enabled=1, delay=0)

    await update.message.reply_text(f"已添加关键词：{'*' if fuzzy else ''}{keyword}")
    # 清理临时数据并返回管理页
    context.user_data.pop("kw_add_step", None)
    context.user_data.pop("kw_new_keyword", None)
    await keywords_setting_entry(update, context)
    return ConversationHandler.END

async def kw_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """删除关键词 - 选择列表"""
    chat_id = get_chat_id(update, context)
    chat_name = get_chat_name(context, chat_id)
    kws = await db.fetch_keywords(chat_id)

    if not kws:
        await update.callback_query.answer("没有可删除的关键词")
        return

    buttons = [
        [
            InlineKeyboardButton(
                f"{'*' if k['fuzzy'] else '-'} {k['keyword']}",
                callback_data=f"kw_remove_{k['keyword']}"
            )
        ]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{chat_name} 关键词管理 - 删除】\n请选择要删除的关键词：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def kw_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理确认删除关键词"""
    chat_id = get_chat_id(update, context)
    keyword = update.callback_query.data.removeprefix("kw_remove_")
    await db.remove_keyword(chat_id, keyword)
    await keywords_setting_entry(update, context)

async def kw_enable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """启用关键词 - 选择列表"""
    chat_id = get_chat_id(update, context)
    chat_name = get_chat_name(context, chat_id)
    kws = await db.fetch_keywords(chat_id)

    if not kws:
        await update.callback_query.answer("没有关键词")
        return

    buttons = [
        [
            InlineKeyboardButton(
                f"{'*' if k['fuzzy'] else '-'} {k['keyword']}",
                callback_data=f"kw_enable_{k['keyword']}"
            )
        ]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{chat_name} 关键词管理 - 启用】\n请选择要启用的关键词：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def kw_enable_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理启用关键词确认"""
    chat_id = get_chat_id(update, context)
    keyword = update.callback_query.data.removeprefix("kw_enable_")
    await db.update_keyword_enable(chat_id, keyword, 1)
    await keywords_setting_entry(update, context)

async def kw_disable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """禁用关键词 - 选择列表"""
    chat_id = get_chat_id(update, context)
    chat_name = get_chat_name(context, chat_id)
    kws = await db.fetch_keywords(chat_id)

    if not kws:
        await update.callback_query.answer("没有关键词")
        return

    buttons = [
        [
            InlineKeyboardButton(
                f"{'*' if k['fuzzy'] else '-'} {k['keyword']}",
                callback_data=f"kw_disable_{k['keyword']}"
            )
        ]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{chat_name} 关键词管理 - 禁用】\n请选择要关闭的关键词：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def kw_disable_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理禁用关键词确认"""
    chat_id = get_chat_id(update, context)
    keyword = update.callback_query.data.removeprefix("kw_disable_")
    await db.update_keyword_enable(chat_id, keyword, 0)
    await keywords_setting_entry(update, context)

async def kw_delay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """设置延时删除 - 选择关键词"""
    chat_id = get_chat_id(update, context)
    chat_name = get_chat_name(context, chat_id)
    delay = int(update.callback_query.data.removeprefix("kw_delay_"))
    context.user_data["kw_delay_set"] = delay

    kws = await db.fetch_keywords(chat_id)
    if not kws:
        await update.callback_query.answer("没有关键词")
        return

    buttons = [
        [
            InlineKeyboardButton(
                f"{'*' if k['fuzzy'] else '-'} {k['keyword']}",
                callback_data=f"kw_delayset_{k['keyword']}"
            )
        ]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{chat_name} 关键词管理 - 延时删除】\n请选择要设置延时删除的关键词（当前{delay}分钟）：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def kw_delayset_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理延时删除确认"""
    chat_id = get_chat_id(update, context)
    keyword = update.callback_query.data.removeprefix("kw_delayset_")
    delay = context.user_data.get("kw_delay_set", 0)
    await db.update_keyword_delay(chat_id, keyword, delay)
    await keywords_setting_entry(update, context)

async def kw_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """编辑关键词 - 选择列表"""
    chat_id = get_chat_id(update, context)
    chat_name = get_chat_name(context, chat_id)
    kws = await db.fetch_keywords(chat_id)

    if not kws:
        await update.callback_query.answer("没有可编辑的关键词")
        return

    buttons = [
        [
            InlineKeyboardButton(
                f"{'*' if k['fuzzy'] else '-'} {k['keyword']}",
                callback_data=f"kw_edit_{k['keyword']}"
            )
        ]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{chat_name} 关键词管理 - 编辑】\n请选择要编辑的关键词：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def kw_edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """进入编辑关键词回复内容"""
    chat_id = get_chat_id(update, context)
    chat_name = get_chat_name(context, chat_id)
    keyword = update.callback_query.data.removeprefix("kw_edit_")
    context.user_data["kw_edit_keyword"] = keyword

    kws = await db.fetch_keywords(chat_id)
    for k in kws:
        if k["keyword"] == keyword:
            old_reply = k["reply"]
            fuzzy = k.get("fuzzy", 0)
            break
    else:
        await update.callback_query.answer("关键词不存在")
        return ConversationHandler.END

    context.user_data["kw_edit_fuzzy"] = fuzzy
    buttons = [
        [
            InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
            InlineKeyboardButton("主菜单", callback_data="main_menu"),
        ]
    ]
    await update.callback_query.edit_message_text(
        f"【{chat_name} 关键词管理 - 编辑】\n"
        f"原关键词：{'*' if fuzzy else ''}{keyword}\n"
        f"原回复：{old_reply}\n\n"
        "请直接发送新的回复内容：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return KW_EDIT

async def kw_edit_save(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """保存编辑后的回复内容"""
    chat_id = get_chat_id(update, context)
    keyword = context.user_data.get("kw_edit_keyword")
    if not keyword:
        await update.message.reply_text("未选择关键词。")
        return ConversationHandler.END

    reply = update.message.text.strip()
    if not reply:
        await update.message.reply_text("回复内容不能为空，请重新输入：")
        return KW_EDIT

    await db.update_keyword_reply(chat_id, keyword, reply)
    await update.message.reply_text("修改成功！")
    context.user_data.pop("kw_edit_keyword", None)
    context.user_data.pop("kw_edit_fuzzy", None)
    await keywords_setting_entry(update, context)
    return ConversationHandler.END

async def keyword_autoreply(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """群组内自动回复"""
    if update.effective_chat.type not in ("group", "supergroup"):
        return

    chat_id = update.effective_chat.id
    kws = await db.fetch_keywords(chat_id)
    text = update.effective_message.text or ""

    for item in kws:
        if not item.get("enabled", True):
            continue

        match = (
            (item.get("fuzzy") and item["keyword"] in text) or
            (not item.get("fuzzy") and item["keyword"] == text)
        )
        if match:
            msg = await update.message.reply_text(item["reply"])
            delay = int(item.get("delay", 0))
            if delay > 0:
                await asyncio.sleep(delay * 60)
                try:
                    await msg.delete()
                except Exception:
                    pass
            break
