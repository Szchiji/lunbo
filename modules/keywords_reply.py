import json
import asyncio
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes

KEYWORD_FILE = "keywords_data.json"  # 新文件，避免和旧文件冲突

def load_keywords():
    try:
        with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_keywords(data):
    with open(KEYWORD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_keywords(chat_id):
    data = load_keywords()
    return data.get(str(chat_id), [])

def set_keywords(chat_id, kwlist):
    data = load_keywords()
    data[str(chat_id)] = kwlist
    save_keywords(data)

def keyword_setting_menu(chat_id):
    kws = get_keywords(chat_id)
    if not kws:
        kw_list = "[空]"
    else:
        kw_list = "\n".join([
            f"{'*' if k.get('fuzzy') else '-'} {k['keyword']} {'✅' if k.get('enabled', True) else '❌'} 延时:{k.get('delay', 0)}分"
            for k in kws
        ])
    text = (
        "关键词回复 [ /命令帮助 ]\n\n"
        f"已添加的关键词:\n{kw_list}\n"
        "- 表示精准触发\n"
        "* 表示包含触发"
    )
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
        ],
        [
            InlineKeyboardButton("返回", callback_data="kw_back"),
        ]
    ]
    return text, InlineKeyboardMarkup(kb)

async def keywords_setting_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text, kb = keyword_setting_menu(user_id)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb)
    else:
        await update.message.reply_text(text, reply_markup=kb)

async def kw_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["kw_add_step"] = "keyword"
    await update.callback_query.edit_message_text("请输入新关键词（前缀*为模糊匹配，如“*你好”）：")

async def kw_add_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get("kw_add_step")
    if step == "keyword":
        kw = update.message.text.strip()
        context.user_data["kw_new_keyword"] = kw
        context.user_data["kw_add_step"] = "reply"
        await update.message.reply_text("请输入该关键词的自动回复内容：")
        return
    elif step == "reply":
        kw = context.user_data.get("kw_new_keyword")
        reply = update.message.text.strip()
        fuzzy = kw.startswith("*")
        keyword = kw.lstrip("*")
        kws = get_keywords(user_id)
        kws.append({"keyword": keyword, "reply": reply, "fuzzy": fuzzy, "enabled": True, "delay": 0})
        set_keywords(user_id, kws)
        await keywords_setting_entry(update, context)
        context.user_data.pop("kw_add_step", None)
        context.user_data.pop("kw_new_keyword", None)
        return

async def kw_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kws = get_keywords(user_id)
    if not kws:
        await update.callback_query.answer("没有可删除的关键词")
        return
    context.user_data["kw_remove"] = True
    buttons = [
        [InlineKeyboardButton(f"{'*' if k['fuzzy'] else '-'} {k['keyword']}", callback_data=f"kw_remove_{idx}")]
        for idx, k in enumerate(kws)
    ]
    buttons.append([InlineKeyboardButton("返回", callback_data="kw_back")])
    await update.callback_query.edit_message_text("请选择要删除的关键词：", reply_markup=InlineKeyboardMarkup(buttons))

async def kw_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    idx = int(update.callback_query.data.replace("kw_remove_", ""))
    kws = get_keywords(user_id)
    if idx < len(kws):
        del kws[idx]
        set_keywords(user_id, kws)
    await keywords_setting_entry(update, context)

async def kw_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await keywords_setting_entry(update, context)

async def kw_enable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kws = get_keywords(user_id)
    if not kws:
        await update.callback_query.answer("没有关键词")
        return
    context.user_data["kw_enable"] = True
    buttons = [
        [InlineKeyboardButton(f"{'*' if k['fuzzy'] else '-'} {k['keyword']}", callback_data=f"kw_enable_{idx}")]
        for idx, k in enumerate(kws)
    ]
    buttons.append([InlineKeyboardButton("返回", callback_data="kw_back")])
    await update.callback_query.edit_message_text("请选择要启用的关键词：", reply_markup=InlineKeyboardMarkup(buttons))

async def kw_enable_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    idx = int(update.callback_query.data.replace("kw_enable_", ""))
    kws = get_keywords(user_id)
    if idx < len(kws):
        kws[idx]["enabled"] = True
        set_keywords(user_id, kws)
    await keywords_setting_entry(update, context)

async def kw_disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kws = get_keywords(user_id)
    if not kws:
        await update.callback_query.answer("没有关键词")
        return
    context.user_data["kw_disable"] = True
    buttons = [
        [InlineKeyboardButton(f"{'*' if k['fuzzy'] else '-'} {k['keyword']}", callback_data=f"kw_disable_{idx}")]
        for idx, k in enumerate(kws)
    ]
    buttons.append([InlineKeyboardButton("返回", callback_data="kw_back")])
    await update.callback_query.edit_message_text("请选择要关闭的关键词：", reply_markup=InlineKeyboardMarkup(buttons))

async def kw_disable_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    idx = int(update.callback_query.data.replace("kw_disable_", ""))
    kws = get_keywords(user_id)
    if idx < len(kws):
        kws[idx]["enabled"] = False
        set_keywords(user_id, kws)
    await keywords_setting_entry(update, context)

async def kw_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 这里可以配合按钮直接设置delay
    user_id = update.effective_user.id
    data = update.callback_query.data
    delay = int(data.replace("kw_delay_", ""))
    context.user_data["kw_delay_set"] = delay
    kws = get_keywords(user_id)
    if not kws:
        await update.callback_query.answer("没有关键词")
        return
    buttons = [
        [InlineKeyboardButton(f"{'*' if k['fuzzy'] else '-'} {k['keyword']}", callback_data=f"kw_delayset_{idx}")]
        for idx, k in enumerate(kws)
    ]
    buttons.append([InlineKeyboardButton("返回", callback_data="kw_back")])
    await update.callback_query.edit_message_text(f"请选择要设置延时删除的关键词（当前设置为{delay}分钟）：", reply_markup=InlineKeyboardMarkup(buttons))

async def kw_delayset_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    idx = int(update.callback_query.data.replace("kw_delayset_", ""))
    delay = context.user_data.get("kw_delay_set", 0)
    kws = get_keywords(user_id)
    if idx < len(kws):
        kws[idx]["delay"] = delay
        set_keywords(user_id, kws)
    await keywords_setting_entry(update, context)

# 群聊自动回复（群内必须加 bot，并有权限）
async def keyword_autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = update.effective_chat.id
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    kws = get_keywords(group_id)
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
