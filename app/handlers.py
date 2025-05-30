from aiogram import types, F
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot import dp
from app.scheduler import schedule_message, remove_job, scheduler
from app.database import add_task, get_all_tasks, delete_task
from app.utils import parse_datetime
from datetime import datetime

class ScheduleStates(StatesGroup):
    waiting_for_file = State()
    waiting_for_caption = State()
    waiting_for_button_decision = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()
    waiting_for_interval = State()
    waiting_for_start_time = State()
    waiting_for_stop_time = State()
    waiting_for_confirmation = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("欢迎使用定时消息机器人！\n命令:\n/add - 添加定时消息\n/view - 查看定时消息\n/delete - 删除定时消息")

@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    await message.answer("请上传一张图片或视频，或发送“跳过”来只发送文本")
    await state.set_state(ScheduleStates.waiting_for_file)

@dp.message(F.content_type.in_({"photo", "video"}), ScheduleStates.waiting_for_file)
async def process_file(message: types.Message, state: FSMContext):
    file_id = None
    file_type = None
    if message.photo:
        file_id = message.photo[-1].file_id  # 取最高质量
        file_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
    await state.update_data(file_id=file_id, file_type=file_type)
    await message.answer("请发送文字内容（消息正文）")
    await state.set_state(ScheduleStates.waiting_for_caption)

@dp.message(lambda m: m.text and m.text.lower() == "跳过", ScheduleStates.waiting_for_file)
async def skip_file(message: types.Message, state: FSMContext):
    # 用户跳过上传文件
    await state.update_data(file_id=None, file_type=None)
    await message.answer("请发送文字内容（消息正文）")
    await state.set_state(ScheduleStates.waiting_for_caption)

@dp.message(ScheduleStates.waiting_for_caption)
async def process_caption(message: types.Message, state: FSMContext):
    await state.update_data(caption=message.text)
    await message.answer("是否添加按钮？回复“是”或“否”")
    await state.set_state(ScheduleStates.waiting_for_button_decision)

@dp.message(lambda m: m.text and m.text.lower() in ["是", "否"], ScheduleStates.waiting_for_button_decision)
async def process_button_decision(message: types.Message, state: FSMContext):
    text = message.text.lower()
    if text == "是":
        await message.answer("请输入按钮文本")
        await state.set_state(ScheduleStates.waiting_for_button_text)
    else:
        await state.update_data(button_text=None, button_url=None)
        await message.answer("请输入间隔时间（单位：秒，输入0表示不循环）")
        await state.set_state(ScheduleStates.waiting_for_interval)

@dp.message(ScheduleStates.waiting_for_button_text)
async def process_button_text(message: types.Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await message.answer("请输入按钮链接 URL")
    await state.set_state(ScheduleStates.waiting_for_button_url)

@dp.message(ScheduleStates.waiting_for_button_url)
async def process_button_url(message: types.Message, state: FSMContext):
    await state.update_data(button_url=message.text)
    await message.answer("请输入间隔时间（单位：秒，输入0表示不循环）")
    await state.set_state(ScheduleStates.waiting_for_interval)

@dp.message(ScheduleStates.waiting_for_interval)
async def process_interval(message: types.Message, state: FSMContext):
    try:
        interval = int(message.text)
        if interval < 0:
            raise ValueError
    except ValueError:
        await message.answer("请输入正确的非负整数秒数")
        return
    await state.update_data(interval_seconds=interval if interval > 0 else None)
    await message.answer("请输入开始时间（格式：YYYY-MM-DD HH:MM），或者发送“现在”表示立即开始")
    await state.set_state(ScheduleStates.waiting_for_start_time)

@dp.message(ScheduleStates.waiting_for_start_time)
async def process_start_time(message: types.Message, state: FSMContext):
    if message.text.lower() == "现在":
        start_time = datetime.now()
    else:
        start_time = parse_datetime(message.text)
        if not start_time:
            await message.answer("时间格式错误，请输入：YYYY-MM-DD HH:MM 或 发送“现在”")
            return
    await state.update_data(start_time=start_time)
    await message.answer("请输入停止时间（格式：YYYY-MM-DD HH:MM），或发送“无限”表示无停止时间")
    await state.set_state(ScheduleStates.waiting_for_stop_time)

@dp.message(ScheduleStates.waiting_for_stop_time)
async def process_stop_time(message: types.Message, state: FSMContext):
    if message.text.lower() == "无限":
        stop_time = None
    else:
        stop_time = parse_datetime(message.text)
        if not stop_time:
            await message.answer("时间格式错误，请输入：YYYY-MM-DD HH:MM 或 发送“无限”")
            return
    await state.update_data(stop_time=stop_time)

    # 预览内容
    data = await state.get_data()
    text_preview = data.get("caption") or ""
    btn_text = data.get("button_text")
    btn_url = data.get("button_url")
    interval = data.get("interval_seconds")
    start = data.get("start_time")
    stop = data.get("stop_time")

    preview_msg = f"请确认定时消息内容：\n\n文字:\n{text_preview}\n"
    if btn_text and btn_url:
        preview_msg += f"按钮: [{btn_text}]({btn_url})\n"
    if interval:
        preview_msg += f"间隔: {interval}秒循环\n"
    else:
        preview_msg += "单次发送\n"
    preview_msg += f"开始时间: {start.strftime('%Y-%m-%d %H:%M') if start else '无'}\n"
    preview_msg += f"停止时间: {stop.strftime('%Y-%m-%d %H:%M') if stop else '无'}\n\n"
    preview_msg += "回复“确认”发送，或“取消”放弃"

    await message.answer(preview_msg, parse_mode="Markdown")
    await state.set_state(ScheduleStates.waiting_for_confirmation)

@dp.message(lambda m: m.text.lower() == "确认", ScheduleStates.waiting_for_confirmation)
async def process_confirmation(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = message.chat.id
    from uuid import uuid4
    job_id = str(uuid4())
    run_time = data.get("start_time").strftime("%Y-%m-%d %H:%M:%S")
    add_task(chat_id=chat_id,
             run_time=run_time,
             message=data.get("caption"),
             job_id=job_id,
             file_id=data.get("file_id"),
             file_type=data.get("file_type"),
             button_text=data.get("button_text"),
             button_url=data.get("button_url"),
             interval_seconds=data.get("interval_seconds"),
             start_time=data.get("start_time").strftime("%Y-%m-%d %H:%M:%S") if data.get("start_time") else None,
             stop_time=data.get("stop_time").strftime("%Y-%m-%d %H:%M:%S") if data.get("stop_time") else None)

    schedule_message(job_id=job_id,
                     chat_id=chat_id,
                     text=data.get("caption"),
                     run_date=data.get("start_time"),
                     file_id=data.get("file_id"),
                     file_type=data.get("file_type"),
                     button_text=data.get("button_text"),
                     button_url=data.get("button_url"),
                     interval_seconds=data.get("interval_seconds"),
                     start_time=data.get("start_time"),
                     stop_time=data.get("stop_time"))

    await message.answer("定时任务已创建！")
    await state.clear()

@dp.message(lambda m: m.text.lower() == "取消", ScheduleStates.waiting_for_confirmation)
async def cancel_confirmation(message: types.Message, state: FSMContext):
    await message.answer("已取消定时消息创建。")
    await state.clear()

@dp.message(Command("view"))
async def view_tasks(message: types.Message):
    tasks = get_all_tasks(message.chat.id)
    if not tasks:
        await message.answer("你没有定时任务。")
        return
    msg = "你的定时任务:\n"
    for t in tasks:
        msg += f"任务ID: {t[0]}，运行时间: {t[2]}, 文字: {t[3]}\n"
    await message.answer(msg)

@dp.message(Command("delete"))
async def delete_command(message: types.Message):
    tasks = get_all_tasks(message.chat.id)
    if not tasks:
        await message.answer("无任务可删除。")
        return
    msg = "发送你要删除的任务ID：\n"
    for t in tasks:
        msg += f"任务ID: {t[0]}，运行时间: {t[2]}, 文字: {t[3]}\n"
    await message.answer(msg)
    await ScheduleStates.waiting_for_confirmation.set()

@dp.message(ScheduleStates.waiting_for_confirmation)
async def process_delete(message: types.Message):
    try:
        task_id = int(message.text)
    except ValueError:
        await message.answer("请输入正确的数字任务ID")
        return
    tasks = get_all_tasks(message.chat.id)
    target = next((t for t in tasks if t[0] == task_id), None)
    if not target:
        await message.answer("未找到该任务ID")
        return

    delete_task(target[4])  # target[4]是job_id字段
    try:
        remove_job(target[4])
    except Exception:
        pass
    await message.answer(f"任务 {task_id} 已删除")
    await dp.current_state(user=message.from_user.id).clear()