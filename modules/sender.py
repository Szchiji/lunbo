import mimetypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

async def send_text(bot, chat_id, text, buttons=None, **kwargs):
    """
    发送纯文本消息，可带按钮
    """
    reply_markup = buttons if buttons else None
    return await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, **kwargs)

async def send_media(bot, chat_id, media_url, caption=None, buttons=None, **kwargs):
    """
    智能判断文件类型发送媒体消息（图片/视频/文档），可带caption和按钮
    """
    mime, _ = mimetypes.guess_type(media_url)
    reply_markup = buttons if buttons else None

    try:
        if not mime:
            # 无法识别类型，按文档方式发送
            return await bot.send_document(chat_id=chat_id, document=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
        if mime.startswith('image/'):
            return await bot.send_photo(chat_id=chat_id, photo=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
        elif mime.startswith('video/'):
            return await bot.send_video(chat_id=chat_id, video=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
        else:
            return await bot.send_document(chat_id=chat_id, document=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
    except Exception as e:
        print(f"[send_media] 发送媒体失败: {e}")
        return None

def build_buttons(buttons_data):
    """
    将数据库中的按钮描述转为 InlineKeyboardMarkup
    支持单行/多行、字符串或数组格式
    buttons_data 示例:
        [
            {"text": "按钮1", "url": "https://xxx"},
            [{"text": "按钮2", "url": "https://yyy"}, {"text": "按钮3", "url": "https://zzz"}]
        ]
    """
    import json
    if not buttons_data:
        return None
    # 支持字符串（数据库存储JSON字符串）或对象
    if isinstance(buttons_data, str):
        try:
            buttons_data = json.loads(buttons_data)
        except Exception:
            return None
    rows = []
    for btn in buttons_data:
        if isinstance(btn, list):
            row = [InlineKeyboardButton(sub.get("text", "--"), url=sub.get("url", "")) for sub in btn]
            rows.append(row)
        else:
            rows.append([InlineKeyboardButton(btn.get("text", "--"), url=btn.get("url", ""))])
    return InlineKeyboardMarkup(rows) if rows else None

async def delete_message(bot, chat_id, message_id):
    """
    删除指定消息
    """
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"[delete_message] 删除消息失败: {e}")

async def pin_message(bot, chat_id, message_id, disable_notification=True):
    """
    置顶指定消息
    """
    try:
        await bot.pin_chat_message(chat_id, message_id, disable_notification=disable_notification)
    except Exception as e:
        print(f"[pin_message] 置顶失败: {e}")
