import asyncio
import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
import db

def build_keywords_text(kws, group_name=""):
    if not kws:
        kw_list = "[空]"
    else:
        kw_list = "\n".join([
            f"{'*' if k.get('fuzzy') else '-'} {k['keyword']} {'✅' if k.get('enabled', True) else '❌'} 延时:{k.get('delay', 0)}分"
            for k in kws
        ])
    text = (
        f"已添加的关键词:\n{kw_list}\n"
        "- 表示精准触发\n"
        "* 表示包含触发"
    )
    return text

def keyword_setting_menu():
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
        ]
    ]
    return InlineKeyboardMarkup(kb)

def get_current_group_id(context, update):
    group_id = context.user_data.get("selected_group_id")
    if group_id: return group_id
    if update.effective_chat: return update.effective_chat.id
    return update.effective_user.id

def get_group_name(context, group_id):
    return (context.bot_data.get("GROUPS", {}) or {}).get(group_id, str(group_id))

async def keywords_setting_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    group_name = get_group_name(context, group_id)
    kws = await db.fetch_keywords(group_id)
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    text = (
        f"📝【{group_name} 关键词管理】\n"
        f"时间：{now_str}\n"
        "（此页可管理关键词自动回复）\n" +
        build_keywords_text(kws, group_name)
    )
    kb = keyword_setting_menu()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb)
    else:
        await update.message.reply_text(text, reply_markup=kb)

async def kw_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["kw_add_step"] = "keyword"
    await update.callback_query.edit_message_text(
        "【关键词管理 - 添加】\n请输入新关键词（前缀*为模糊匹配，如“*你好”）：",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
             InlineKeyboardButton("主菜单", callback_data="main_menu")]
        ])
    )

async def kw_add_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    step = context.user_data.get("kw_add_step")
    if step == "keyword":
        kw = update.message.text.strip()
        context.user_data["kw_new_keyword"] = kw
        context.user_data["kw_add_step"] = "reply"
        await update.message.reply_text(
            "请输入该关键词的自动回复内容：\n（如需取消，请点击下方按钮）",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
                 InlineKeyboardButton("主菜单", callback_data="main_menu")]
            ])
        )
        return
    elif step == "reply":
        kw = context.user_data.get("kw_new_keyword")
        reply = update.message.text.strip()
        fuzzy = kw.startswith("*")
        keyword = kw.lstrip("*")
        await db.add_keyword(group_id, keyword, reply, int(fuzzy), 1, 0)
        await keywords_setting_entry(update, context)
        context.user_data.pop("kw_add_step", None)
        context.user_data.pop("kw_new_keyword", None)
        return

async def kw_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    group_name = get_group_name(context, group_id)
    kws = await db.fetch_keywords(group_id)
    if not kws:
        await update.callback_query.answer("没有可删除的关键词")
        return
    buttons = [
        [InlineKeyboardButton(f"{'*' if k['fuzzy'] else '-'} {k['keyword']}", callback_data=f"kw_remove_{k['keyword']}")]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{group_name} 关键词管理 - 删除】\n请选择要删除的关键词：",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def kw_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    keyword = update.callback_query.data.replace("kw_remove_", "")
    await db.remove_keyword(group_id, keyword)
    await keywords_setting_entry(update, context)

async def kw_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await keywords_setting_entry(update, context)

async def kw_enable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    group_name = get_group_name(context, group_id)
    kws = await db.fetch_keywords(group_id)
    if not kws:
        await update.callback_query.answer("没有关键词")
        return
    buttons = [
        [InlineKeyboardButton(f"{'*' if k['fuzzy'] else '-'} {k['keyword']}", callback_data=f"kw_enable_{k['keyword']}")]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{group_name} 关键词管理 - 启用】\n请选择要启用的关键词：",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def kw_enable_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    keyword = update.callback_query.data.replace("kw_enable_", "")
    await db.update_keyword_enable(group_id, keyword, 1)
    await keywords_setting_entry(update, context)

async def kw_disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    group_name = get_group_name(context, group_id)
    kws = await db.fetch_keywords(group_id)
    if not kws:
        await update.callback_query.answer("没有关键词")
        return
    buttons = [
        [InlineKeyboardButton(f"{'*' if k['fuzzy'] else '-'} {k['keyword']}", callback_data=f"kw_disable_{k['keyword']}")]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{group_name} 关键词管理 - 禁用】\n请选择要关闭的关键词：",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def kw_disable_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    keyword = update.callback_query.data.replace("kw_disable_", "")
    await db.update_keyword_enable(group_id, keyword, 0)
    await keywords_setting_entry(update, context)

async def kw_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    group_name = get_group_name(context, group_id)
    data = update.callback_query.data
    delay = int(data.replace("kw_delay_", ""))
    context.user_data["kw_delay_set"] = delay
    kws = await db.fetch_keywords(group_id)
    if not kws:
        await update.callback_query.answer("没有关键词")
        return
    buttons = [
        [InlineKeyboardButton(f"{'*' if k['fuzzy'] else '-'} {k['keyword']}", callback_data=f"kw_delayset_{k['keyword']}")]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{group_name} 关键词管理 - 延时删除】\n请选择要设置延时删除的关键词（当前设置为{delay}分钟）：",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def kw_delayset_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    keyword = update.callback_query.data.replace("kw_delayset_", "")
    delay = context.user_data.get("kw_delay_set", 0)
    await db.update_keyword_delay(group_id, keyword, delay)
    await keywords_setting_entry(update, context)

async def kw_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    group_name = get_group_name(context, group_id)
    kws = await db.fetch_keywords(group_id)
    if not kws:
        await update.callback_query.answer("没有可编辑的关键词")
        return
    buttons = [
        [InlineKeyboardButton(f"{'*' if k['fuzzy'] else '-'} {k['keyword']}", callback_data=f"kw_edit_{k['keyword']}")]
        for k in kws
    ]
    buttons.append([
        InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
        InlineKeyboardButton("主菜单", callback_data="main_menu"),
    ])
    await update.callback_query.edit_message_text(
        f"【{group_name} 关键词管理 - 编辑】\n请选择要编辑的关键词：",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def kw_edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    group_name = get_group_name(context, group_id)
    keyword = update.callback_query.data.replace("kw_edit_", "")
    context.user_data["kw_edit_keyword"] = keyword
    kws = await db.fetch_keywords(group_id)
    for k in kws:
        if k['keyword'] == keyword:
            old_reply = k['reply']
            fuzzy = k.get('fuzzy', 0)
            break
    else:
        await update.callback_query.answer("关键词不存在")
        return
    context.user_data['kw_edit_fuzzy'] = fuzzy
    await update.callback_query.edit_message_text(
        f"【{group_name} 关键词管理 - 编辑】\n原关键词：{'*' if fuzzy else ''}{keyword}\n原回复内容：{old_reply}\n\n请直接发送新的回复内容：",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("返回上一级", callback_data="back_to_prev"),
             InlineKeyboardButton("主菜单", callback_data="main_menu")]
        ])
    )

async def kw_edit_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = get_current_group_id(context, update)
    keyword = context.user_data.get("kw_edit_keyword")
    fuzzy = context.user_data.get("kw_edit_fuzzy", 0)
    if not keyword:
        await update.message.reply_text("未选择关键词。")
        return
    reply = update.message.text.strip()
    await db.update_keyword_reply(group_id, keyword, reply)
    await update.message.reply_text("修改成功！")
    context.user_data.pop("kw_edit_keyword", None)
    context.user_data.pop("kw_edit_fuzzy", None)
    await keywords_setting_entry(update, context)

async def keyword_autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = update.effective_chat.id
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    kws = await db.fetch_keywords(group_id)
    text = update.effective_message.text or ""
    for item in kws:
        if not item.get("enabled", True):
            continue
        if item["fuzzy"] and item["keyword"] in text:
            m = await update.message.reply_text(item["reply"])
            delay = int(item.get("delay", 0))
            if delay > 0:
                await asyncio.sleep(delay * 60)
                try:
                    await m.delete()
                except Exception:
                    pass
            break
        elif not item["fuzzy"] and item["keyword"] == text:
            m = await update.message.reply_text(item["reply"])
            delay = int(item.get("delay", 0))
            if delay > 0:
                await asyncio.sleep(delay * 60)
                try:
                    await m.delete()
                except Exception:
                    pass
            break
