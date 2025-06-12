from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def schedule_list_menu(schedules):
    keyboard = []
    for msg in schedules:
        state = '✅' if msg['status'] else '❌'
        label = f"{state} {msg['text'][:12]}..."
        keyboard.append([InlineKeyboardButton(label, callback_data=f"edit_{msg['id']}")])
    keyboard.append([InlineKeyboardButton("➕ 添加", callback_data="schedule_add")])
    return InlineKeyboardMarkup(keyboard)

def schedule_edit_menu(schedule):
    status = schedule['status']
    remove_last = schedule['remove_last']
    pin = schedule['pin']
    keyboard = [
        [
            InlineKeyboardButton(f"状态: {'✅启用' if status else '❌关闭'}", callback_data=f"toggle_status_{schedule['id']}"),
            InlineKeyboardButton("删除上一条: " + ("✅是" if remove_last else "❌否"), callback_data=f"toggle_remove_last_{schedule['id']}"),
            InlineKeyboardButton("置顶: " + ("✅是" if pin else "❌否"), callback_data=f"toggle_pin_{schedule['id']}")
        ],
        [
            InlineKeyboardButton("📝 修改文本", callback_data=f"edit_text_{schedule['id']}"),
            InlineKeyboardButton("🖼️ 修改媒体", callback_data=f"edit_media_{schedule['id']}"),
            InlineKeyboardButton("🔗 修改按钮", callback_data=f"edit_button_{schedule['id']}"),
        ],
        [
            InlineKeyboardButton("🔁 重复时间", callback_data=f"edit_repeat_{schedule['id']}"),
            InlineKeyboardButton("🕒 设置时段", callback_data=f"edit_time_period_{schedule['id']}"),
        ],
        [
            InlineKeyboardButton("📅 开始日期", callback_data=f"edit_start_date_{schedule['id']}"),
            InlineKeyboardButton("📅 结束日期", callback_data=f"edit_end_date_{schedule['id']}"),
        ],
        [
            InlineKeyboardButton("🗑️ 删除本条", callback_data=f"delete_{schedule['id']}"),
            InlineKeyboardButton("⬅️ 返回", callback_data="schedule_list"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
