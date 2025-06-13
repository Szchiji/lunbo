from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def schedule_list_menu(schedules):
    """
    生成定时消息列表菜单
    - 有定时消息时，每条显示为按钮，可点击进入设置
    - 没有定时消息时，显示“暂无定时消息”
    - 永远有“➕ 添加定时消息”按钮
    """
    keyboard = []
    if schedules and len(schedules) > 0:
        for sch in schedules:
            txt = sch.get('text', '')[:20] + ("..." if len(sch.get('text', '')) > 20 else "")
            # 可以根据需要补充显示频率、状态等
            keyboard.append([InlineKeyboardButton(txt or "无文本", callback_data=f"edit_{sch['id']}")])
    else:
        # 没有定时消息时，提示不可点
        keyboard.append([InlineKeyboardButton("暂无定时消息", callback_data="noop")])
    keyboard.append([InlineKeyboardButton("➕ 添加定时消息", callback_data="add_schedule")])
    return InlineKeyboardMarkup(keyboard)

def schedule_edit_menu(schedule):
    """
    生成定时消息编辑菜单
    """
    keyboard = [
        [
            InlineKeyboardButton(f"状态: {'✅启用' if schedule.get('status') else '❌关闭'}", callback_data=f"toggle_status_{schedule['id']}"),
            InlineKeyboardButton(f"删除上一条: {'✅' if schedule.get('remove_last') else '❌'}", callback_data=f"toggle_remove_last_{schedule['id']}"),
            InlineKeyboardButton(f"置顶: {'✅' if schedule.get('pin') else '❌'}", callback_data=f"toggle_pin_{schedule['id']}"),
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
            [InlineKeyboardButton("保存", callback_data="confirm_save"), InlineKeyboardButton("取消", callback_data="cancel_add")]
        ]
    elif step:
        btns = [[InlineKeyboardButton("取消", callback_data="cancel_add")]]
    return InlineKeyboardMarkup(btns) if btns else None

def group_select_menu(groups):
    """
    生成群聊选择菜单
    :param groups: dict, 例如 {chat_id1: '群名1', chat_id2: '群名2'}
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=f"set_group_{gid}")]
        for gid, name in groups.items()
    ])
