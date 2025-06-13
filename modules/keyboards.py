from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def schedule_list_menu(schedules):
    keyboard = []
    if schedules and len(schedules) > 0:
        for sch in schedules:
            status = "✅" if sch.get('status', 1) else "❌"
            repeat = sch.get('repeat_seconds', 0)
            rep_str = f"{repeat//60}分钟" if repeat else "单次"
            txt = sch.get('text', '')[:18].replace('\n', ' ')
            if len(sch.get('text', '')) > 18:
                txt += "..."
            btn_text = f"{status} {rep_str} | {txt}" if txt else f"{status} {rep_str}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"edit_menu_{sch['id']}")])
    else:
        keyboard.append([InlineKeyboardButton("暂无定时消息", callback_data="noop")])
    keyboard.append([InlineKeyboardButton("➕ 添加定时消息", callback_data="add_schedule")])
    return InlineKeyboardMarkup(keyboard)

def schedule_edit_menu(schedule):
    keyboard = [
        [
            InlineKeyboardButton(f"状态: {'✅启用' if schedule.get('status') else '❌关闭'}", callback_data=f"toggle_status_{schedule['id']}"),
            InlineKeyboardButton(f"置顶: {'✅' if schedule.get('pin') else '❌'}", callback_data=f"toggle_pin_{schedule['id']}"),
        ],
        [
            InlineKeyboardButton(f"删除上一条: {'✅' if schedule.get('remove_last') else '❌'}", callback_data=f"toggle_remove_last_{schedule['id']}"),
            
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
            InlineKeyboardButton("🔙返回", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def schedule_add_menu(step=None):
    btns = []
    if step == "confirm":
        btns = [
            [InlineKeyboardButton("保存", callback_data="confirm_save"),
             InlineKeyboardButton("取消", callback_data="cancel_add")]
        ]
    elif step:
        btns = [[InlineKeyboardButton("取消", callback_data="cancel_add")]]
    return InlineKeyboardMarkup(btns) if btns else None

def group_select_menu(groups):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=f"set_group_{gid}")]
        for gid, name in groups.items()
    ])
