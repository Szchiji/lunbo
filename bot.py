import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz
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
    CallbackContext,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# === 环境变量检查 ===
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
ADMIN_ID = os.getenv('ADMIN_ID')
TIMEZONE = os.getenv('TIMEZONE', 'Asia/Shanghai')

# 验证必要的环境变量
if not TELEGRAM_BOT_TOKEN or not CHAT_ID:
    print("错误：缺少必要的环境变量！")
    print("请确保设置了 TELEGRAM_BOT_TOKEN 和 CHAT_ID")
    sys.exit(1)

print("环境变量验证通过，正在启动机器人...")

# === 全局变量 ===
rotating_messages: Dict[int, Dict] = {}
next_message_id = 1
sent_messages = {}
timezone = pytz.timezone(TIMEZONE)
scheduler = AsyncIOScheduler(timezone=timezone)

# === 实用函数 ===
async def send_scheduled_messages():
    """发送所有符合条件的轮播消息"""
    now = datetime.now(timezone)
    messages_to_remove = []
    
    for msg_id, msg_data in rotating_messages.items():
        # 检查消息是否在有效期内
        if msg_data['start_time'] <= now <= msg_data['end_time']:
            # 检查是否已经发送过（避免重复发送）
            if not msg_data.get('last_sent') or (now - msg_data['last_sent']) >= timedelta(minutes=1):
                try:
                    # 创建按钮键盘
                    keyboard = []
                    if msg_data.get('buttons'):
                        for btn in msg_data['buttons']:
                            keyboard.append([InlineKeyboardButton(btn['text'], callback_data=f"msg_{msg_id}_{btn['action']}")])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                    
                    # 发送消息
                    sent_msg = await bot.send_message(
                        chat_id=CHAT_ID,
                        text=msg_data['content'],
                        reply_markup=reply_markup
                    )
                    
                    # 存储已发送消息用于按钮回调
                    sent_messages[sent_msg.message_id] = msg_id
                    rotating_messages[msg_id]['last_sent'] = now
                    print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} - 发送消息 ID {msg_id}: {msg_data['content'][:50]}...")
                except Exception as e:
                    print(f"发送消息 {msg_id} 时出错: {e}")
        
        # 标记过期的消息
        if now > msg_data['end_time']:
            messages_to_remove.append(msg_id)
    
    # 移除过期的消息
    for msg_id in messages_to_remove:
        rotating_messages.pop(msg_id, None)
        print(f"消息 ID {msg_id} 已过期并移除")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
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

# === 命令处理函数 ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    await update.message.reply_text("🚀 高级轮播机器人已启动! 使用 /help 查看可用命令")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    help_text = """
📢 高级轮播机器人命令:

/add - 添加新轮播消息
/list - 查看所有轮播消息
/remove <ID> - 删除指定消息
/status - 查看当前状态

📝 添加消息格式:
/add "消息内容" "开始时间" "结束时间" "按钮1文本:动作1,按钮2文本:动作2"

⏰ 时间格式:
YYYY-MM-DD HH:MM (24小时制)

🌐 示例:
/add "今日特价商品..." "2023-12-01 09:00" "2023-12-31 21:00" "查看详情:view_details,立即购买:buy_now"
"""
    await update.message.reply_text(help_text)

async def add_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /add 命令"""
    # 权限检查
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("🚫 只有管理员可以执行此操作")
        return
    
    # 检查参数数量
    if len(context.args) < 3:
        await update.message.reply_text("""
❌ 参数不足! 使用方法:
/add "消息内容" "开始时间" "结束时间" [可选:"按钮1文本:动作1,按钮2文本:动作2"]

示例:
/add "今日特价商品..." "2023-12-01 09:00" "2023-12-31 21:00" "查看详情:view_details,立即购买:buy_now"
""")
        return
    
    try:
        global next_message_id
        content = context.args[0]
        start_time = datetime.strptime(context.args[1], "%Y-%m-%d %H:%M").astimezone(timezone)
        end_time = datetime.strptime(context.args[2], "%Y-%m-%d %H:%M").astimezone(timezone)
        
        # 处理按钮
        buttons = []
        if len(context.args) > 3:
            for btn_info in context.args[3].split(','):
                if ':' in btn_info:
                    btn_text, btn_action = btn_info.split(':', 1)
                    buttons.append({'text': btn_text.strip(), 'action': btn_action.strip()})
        
        # 存储消息
        rotating_messages[next_message_id] = {
            'content': content,
            'start_time': start_time,
            'end_time': end_time,
            'buttons': buttons,
            'last_sent': None
        }
        
        # 发送确认消息
        response = (
            f"✅ 已添加消息 (ID: {next_message_id})\n"
            f"📝 内容: {content[:100]}{'...' if len(content) > 100 else ''}\n"
            f"⏰ 时间: {start_time.strftime('%Y-%m-%d %H:%M')} 到 {end_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"🔘 按钮: {len(buttons)} 个"
        )
        
        await update.message.reply_text(response)
        next_message_id += 1
    except Exception as e:
        await update.message.reply_text(f"❌ 添加失败: {str(e)}")

async def list_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /list 命令"""
    if not rotating_messages:
        await update.message.reply_text("📭 当前没有轮播消息")
        return
    
    messages = []
    now = datetime.now(timezone)
    
    for msg_id, msg_data in rotating_messages.items():
        # 确定消息状态
        if now < msg_data['start_time']:
            status = "⏳ 等待中"
        elif msg_data['start_time'] <= now <= msg_data['end_time']:
            status = "✅ 活跃中"
        else:
            status = "❌ 已过期"
        
        # 格式化消息信息
        messages.append(
            f"🆔 ID: {msg_id} | {status}\n"
            f"⏰ 时间: {msg_data['start_time'].strftime('%Y-%m-%d %H:%M')} - "
            f"{msg_data['end_time'].strftime('%Y-%m-%d %H:%M')}\n"
            f"📝 内容: {msg_data['content'][:50]}...\n"
            f"🔘 按钮: {len(msg_data.get('buttons', []))} 个\n"
        )
    
    # 分页发送消息（避免消息过长）
    full_text = "\n".join(messages)
    for i in range(0, len(full_text), 4000):
        await update.message.reply_text(full_text[i:i+4000])

async def remove_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /remove 命令"""
    # 权限检查
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("🚫 只有管理员可以执行此操作")
        return
    
    # 检查参数
    if not context.args:
        await update.message.reply_text("❌ 请输入要删除的消息ID\n示例: /remove 1")
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

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /status 命令"""
    now = datetime.now(timezone)
    active_count = sum(
        1 for msg in rotating_messages.values()
        if msg['start_time'] <= now <= msg['end_time']
    )
    pending_count = sum(
        1 for msg in rotating_messages.values()
        if now < msg['start_time']
    )
    expired_count = sum(
        1 for msg in rotating_messages.values()
        if now > msg['end_time']
    )
    
    status_text = (
        f"📊 机器人状态报告\n"
        f"⏰ 时区: {TIMEZONE}\n"
        f"📅 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📋 消息统计:\n"
        f"  - 总消息数: {len(rotating_messages)}\n"
        f"  - 活跃消息: {active_count}\n"
        f"  - 等待消息: {pending_count}\n"
        f"  - 过期消息: {expired_count}\n"
        f"🔄 下次发送检查: {now.replace(second=0, microsecond=0) + timedelta(minutes=1)}"
    )
    
    await update.message.reply_text(status_text)

# === 主函数 ===
def main():
    # 初始化机器人
    try:
        global bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        print("机器人初始化成功！")
    except Exception as e:
        print(f"机器人初始化失败: {e}")
        sys.exit(1)
    
    # 创建应用
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # 添加命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_message))
    application.add_handler(CommandHandler("list", list_messages))
    application.add_handler(CommandHandler("remove", remove_message))
    application.add_handler(CommandHandler("status", status_command))
    
    # 添加按钮回调处理器
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # 设置定时任务
    print("设置定时任务...")
    scheduler.add_job(send_scheduled_messages, 'interval', minutes=1)
    scheduler.start()
    
    print("高级轮播机器人启动...")
    application.run_polling()

if __name__ == '__main__':
    main()