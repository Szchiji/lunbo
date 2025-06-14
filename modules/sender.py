import mimetypes

async def send_media(bot, chat_id, media_url, caption=None, buttons=None, media_type=None, **kwargs):
    reply_markup = buttons if buttons else None
    if media_type:
        try:
            if media_type == "photo":
                return await bot.send_photo(chat_id=chat_id, photo=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
            elif media_type == "video":
                return await bot.send_video(chat_id=chat_id, video=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
            elif media_type == "animation":
                return await bot.send_animation(chat_id=chat_id, animation=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
            elif media_type == "sticker":
                return await bot.send_sticker(chat_id=chat_id, sticker=media_url, **kwargs)
            elif media_type in ["document", "file"]:
                return await bot.send_document(chat_id=chat_id, document=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
            else:
                return await bot.send_document(chat_id=chat_id, document=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
        except Exception as e:
            print(f"[send_media] 按 media_type 发送失败: {e}")
    if isinstance(media_url, str) and media_url.startswith("http"):
        mime, _ = mimetypes.guess_type(media_url)
        try:
            if not mime:
                return await bot.send_document(chat_id=chat_id, document=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
            if mime.startswith('image/'):
                return await bot.send_photo(chat_id=chat_id, photo=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
            elif mime.startswith('video/'):
                return await bot.send_video(chat_id=chat_id, video=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
            else:
                return await bot.send_document(chat_id=chat_id, document=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
        except Exception as e:
            print(f"[send_media] mimetype 发送失败: {e}")
    try:
        return await bot.send_document(chat_id=chat_id, document=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
    except Exception as e1:
        try:
            return await bot.send_video(chat_id=chat_id, video=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
        except Exception as e2:
            try:
                return await bot.send_photo(chat_id=chat_id, photo=media_url, caption=caption, reply_markup=reply_markup, **kwargs)
            except Exception as e3:
                print(f"[send_media] fallback all failed: doc:{e1} video:{e2} photo:{e3}")
                return None

async def delete_message(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"[delete_message] 删除消息失败: {e}")

async def pin_message(bot, chat_id, message_id, disable_notification=True):
    try:
        await bot.pin_chat_message(chat_id, message_id, disable_notification=disable_notification)
    except Exception as e:
        print(f"[pin_message] 置顶失败: {e}")
