from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def schedule_list_menu(schedules):
    """
    生成定时消息列表菜单
    """
    keyboard = []
    for sch in schedules:
        txt = sch['text'][:20] + ("..." if len(sch['text']) > 20 else "")
        keyboard.append([InlineKeyboardButton(txt or "无文本", callback_data=f"edit_{sch['id']}")])
    keyboard.append([InlineKeyboardButton("➕ 添加", callback_data="add_schedule")])
    return InlineKeyboardMarkup(keyboard)

def schedule_edit_menu(schedule):
    """
    生成定时消息编辑菜单
    """
    keyboard = [
        [
            InlineKeyboardButton(f"状态: {'✅启用' if schedule['status'] else '❌关闭'}", callback_data=f"toggle_status_{schedule['id']}"),
            InlineKeyboardButton(f"删除上一条: {'✅' if schedule['remove_last'] else '❌'}", callback_data=f"toggle_remove_last_{schedule['id']}"),
            InlineKeyboardButton(f"置顶: {'✅' if schedule['pin'] else '❌'}", callback_data=f"toggle_pin_{schedule['id']}"),
        ],
        [
            InlineKeyboardButton("📝修改文本", callback_data=f"edit_text_{schedule['id']}"),
            InlineKeyboardButton("🖼修改媒体", callback_data=f"edit_media_{schedule['id']}"),
            InlineKeyboardButton("🔗修改按钮", callback_data=f"edit_button_{schedule['id']}"),
        ],
        [
            InlineKeyboardButton("🔁重复时间", callback_data=f"edit_repeat_{schedule['id']}"),
            InlineKeyboardButton("⏰设置时段", callback_data=f"edit_time_period_{schedule['id']}"),
        ],
        [
            InlineKeyboardButton("📅开始日期", callback_data=f"edit_start_date_{schedule['id']}"),
            InlineKeyboardButton("📅结束日期", callback_data=f"edit_end_date_{schedule['id']}"),
        ],
        [
            InlineKeyboardButton("🗑删除本条", callback_data=f"delete_{schedule['id']}"),
            InlineKeyboardButton("🔙返回", callback_data="schedule_list"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def schedule_add_menu(step=None):
    """
    生成添加定时消息时的确认菜单
    """
    btns = []
    if step == "confirm":
        btns = [
            [InlineKeyboardButton("保存", callback_data="save_add"), InlineKeyboardButton("取消", callback_data="cancel_add")]
        ]
    elif step:
        btns = [[InlineKeyboardButton("取消", callback_data="cancel_add")]]
    return InlineKeyboardMarkup(btns) if btns else None
