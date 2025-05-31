import os
import asyncio
from datetime import datetime, timedelta
from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)
import pytz
import json
from typing import List, Dict, Optional

# 配置参数
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')  # 群组或频道的ID
ADMIN_ID = os.getenv('ADMIN_ID')  # 管理员ID
TIMEZONE = os.getenv('TIMEZONE', 'Asia/Shanghai')  # 默认时区

# 存储轮播消息的数据结构
# 格式: {message_id: {content: str, buttons: list, start_time: datetime, end_time: datetime}}
rotating_messages: Dict[int, Dict] = {}
next_message_id = 1

bot = Bot(token=TELEGRAM_BOT_TOKEN)
timezone = pytz.timezone(TIMEZONE)

# 存储已发送的消息，用于按钮回调
sent_messages = {}

async def send_scheduled_messages(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone)
    messages_to_remove = []
    
    for msg_id, msg_data in rotating_messages.items():
        if msg_data['start_time'] <= now <= msg_data['end_time']:
            # 检查是否已经发送过（避免重复发送）
            if not msg_data.get('last_sent') or (now - msg_data['last_sent']) >= timedelta(hours=1):
                try:
                    keyboard = []
                    if msg_data.get('buttons'):
                        for btn in msg_data['buttons']:
                            keyboard.append([InlineKeyboardButton(btn['text'], callback_data=f"msg_{msg_id}_{btn['action']}")])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                    
                    sent_msg = await bot.send_message(
                        chat_id=CHAT_ID,
                        text=msg_data['content'],
                        reply_markup=reply_markup
                    )
                    
                    # 存储已发送消息用于按钮回调
                    sent_messages[sent_msg.message_id] = msg_id
                    msg_data['last_sent'] = now
                    print(f"{now} - 发送消息ID {msg_id}: {msg_data['content'][:50]}...")
                except Exception as e:
                    print(f"发送消息 {msg_id} 时出错: {e}")
        
        # 标记过期的消息
        if now > msg_data['end_time']:
            messages_to_remove.append(msg_id)
    
    # 移除过期的消息
    for msg_id in messages_to_remove:
        rotating_messages.pop(msg_id, None)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 解析回调数据: msg_1_actionName
    parts = query.data.split('_')
    if len(parts) != 3:
        return
    
    msg_id = int(parts[1])
    action = parts[2]
    
    if msg_id in rotating_messages:
        msg_data = rotating_messages[msg_id]
        # 这里可以根据action执行不同的操作
        await query.edit_message_text(
            text=f"{msg_data['content']}\n\n✅ 已执行操作: {action}",
            reply_markup=query.message.reply_markup
        )

# 命令处理函数
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("高级轮播机器人已启动! 使用 /help 查看可用命令")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📢 高级轮播机器人命令:

/add - 添加新轮播消息
/list - 查看所有轮播消息
/remove <ID> - 删除指定消息
/edit <ID> - 修改消息
/status - 查看当前状态

每条消息可以设置:
- 内容
- 开始和结束时间
- 互动按钮
"""
    await update.message.reply_text(help_text)

async def add_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("🚫 只有管理员可以执行此操作")
        return
    
    # 这里应该是一个多步骤的对话流程
    # 简化版: 使用命令参数
    if len(context.args) < 4:
        await update.message.reply_text("""
使用方法:
/add "消息内容" "YYYY-MM-DD HH:MM" "YYYY-MM-DD HH:MM" "按钮1文本:动作1,按钮2文本:动作2"

示例:
/add "今日特价商品..." "2023-12-01 09:00" "2023-12-31 21:00" "查看详情:view_details,立即购买:buy_now"
""")
        return
    
    try:
        global next_message_id
        content = context.args[0]
        start_time = datetime.strptime(context.args[1], "%Y-%m-%d %H:%M").astimezone(timezone)
        end_time = datetime.strptime(context.args[2], "%Y-%m-%d %H:%M").astimezone(timezone)
        
        buttons = []
        if len(context.args) > 3:
            for btn_info in context.args[3].split(','):
                if ':' in btn_info:
                    btn_text, btn_action = btn_info.split(':', 1)
                    buttons.append({'text': btn_text, 'action': btn_action})
        
        rotating_messages[next_message_id] = {
            'content': content,
            'start_time': start_time,
            'end_time': end_time,
            'buttons': buttons,
            'last_sent': None
        }
        
        await update.message.reply_text(
            f"✅ 已添加消息 (ID: {next_message_id})\n"
            f"内容: {content[:50]}...\n"
            f"时间: {start_time} 到 {end_time}\n"
            f"按钮: {len(buttons)} 个"
        )
        
        next_message_id += 1
    except Exception as e:
        await update.message.reply_text(f"❌ 添加失败: {e}")

async def list_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rotating_messages:
        await update.message.reply_text("当前没有轮播消息")
        return
    
    messages = []
    now = datetime.now(timezone)
    
    for msg_id, msg_data in rotating_messages.items():
        status = "✅ 活跃" if msg_data['start_time'] <= now <= msg_data['end_time'] else "⏸ 未激活"
        messages.append(
            f"ID: {msg_id} {status}\n"
            f"时间: {msg_data['start_time'].strftime('%Y-%m-%d %H:%M')} "
            f"到 {msg_data['end_time'].strftime('%Y-%m-%d %H:%M')}\n"
            f"内容: {msg_data['content'][:50]}...\n"
            f"按钮: {len(msg_data.get('buttons', []))} 个\n"
        )
    
    await update.message.reply_text("当前轮播消息:\n\n" + "\n".join(messages))

async def remove_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("🚫 只有管理员可以执行此操作")
        return
    
    if not context.args:
        await update.message.reply_text("请输入要删除的消息ID")
        return
    
    try:
        msg_id = int(context.args[0])
        if msg_id in rotating_messages:
            rotating_messages.pop(msg_id)
            await update.message.reply_text(f"✅ 已删除消息 ID: {msg_id}")
        else:
            await update.message.reply_text("❌ 找不到指定的消息ID")
    except ValueError:
        await update.message.reply_text("❌ 请输入有效的消息ID")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone)
    active_count = sum(
        1 for msg in rotating_messages.values()
        if msg['start_time'] <= now <= msg['end_time']
    )
    
    status_text = f"""
📊 机器人状态:
时区: {TIMEZONE}
当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}
总消息数: {len(rotating_messages)}
活跃消息: {active_count}
"""
    await update.message.reply_text(status_text)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # 添加命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("add", add_message))
    application.add_handler(CommandHandler("list", list_messages))
    application.add_handler(CommandHandler("remove", remove_message))
    application.add_handler(CommandHandler("status", status))
    
    # 添加按钮回调处理器
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # 启动定时任务，每分钟检查一次
    application.job_queue.run_repeating(
        send_scheduled_messages,
        interval=60,  # 60秒
        first=10
    )
    
    print("高级轮播机器人启动...")
    application.run_polling()

if __name__ == '__main__':
    main()
