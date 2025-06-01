from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import json

def build_buttons(buttons_json):
    if not buttons_json:
        return None
    try:
        btn_list = json.loads(buttons_json)
        keyboard = []
        for btn in btn_list:
            keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
        return InlineKeyboardMarkup(keyboard)
    except:
        return None

def format_task_preview(task):
    text = f"任务ID: {task['id']}\n"
    text += f"内容: {task['content']}\n"
    text += f"媒体类型: {task.get('message_type', '无')}\n"
    text += f"间隔(小时): {task['interval']}\n"
    text += f"开始时间: {task['start_time']}\n"
    text += f"结束时间: {task['end_time'] or '无限'}\n"
    if task.get('buttons'):
        try:
            btns = json.loads(task['buttons'])
            if btns:
                text += "按钮:\n"
                for b in btns:
                    text += f"- {b['text']} -> {b['url']}\n"
        except:
            pass
    return text