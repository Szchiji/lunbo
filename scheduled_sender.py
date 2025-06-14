import asyncio
from telegram import Bot
from db import fetch_schedules, update_schedule_multi
from config import BOT_TOKEN, GROUPS

async def scheduled_sender(application, group_ids):
    bot = application.bot if hasattr(application, 'bot') else Bot(token=BOT_TOKEN)
    print(f"定时消息调度器启动，目标: {group_ids}")
    while True:
        try:
            for group_id in group_ids:
                schedules = await fetch_schedules(group_id)
                for sch in schedules:
                    # 检查时间/周期等逻辑（略，假设需要发送）
                    # 检查是否需要删除上一条
                    if sch.get("remove_last"):
                        last_msg_id = sch.get("last_message_id")
                        if last_msg_id:
                            try:
                                await bot.delete_message(chat_id=group_id, message_id=last_msg_id)
                            except Exception as e:
                                print(f"[scheduled_sender] 删除上一条失败: {e}")
                    # 发送消息
                    try:
                        send_args = {
                            "chat_id": group_id,
                            "text": sch.get("text", "")
                        }
                        msg = None
                        if sch.get("media_url"):
                            # 这里假设是图片，可根据你的实际类型处理
                            msg = await bot.send_photo(chat_id=group_id, photo=sch["media_url"], caption=sch.get("text", ""))
                        else:
                            msg = await bot.send_message(**send_args)
                        # 发送按钮等略
                        # 保存新消息的 message_id
                        await update_schedule_multi(sch["id"], last_message_id=msg.message_id)
                        # 置顶
                        if sch.get("pin"):
                            try:
                                await bot.pin_chat_message(group_id, msg.message_id, disable_notification=True)
                            except Exception as e:
                                print(f"[scheduled_sender] 置顶失败: {e}")
                    except Exception as e:
                        print(f"[scheduled_sender] 发送消息失败: {e}")
        except Exception as e:
            print(f"[scheduled_sender] 主循环异常: {e}")
        await asyncio.sleep(60)  # 每分钟轮询一次，可按需调整
