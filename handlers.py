from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot_init import dp, bot
from scheduler import schedule_message
from database import add_task
from utils import parse_datetime

class ScheduleState(StatesGroup):
    waiting_for_media = State()
    waiting_for_text = State()
    waiting_for_button = State()
    waiting_for_interval = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    confirmation = State()

@dp.message(commands=["start"])
async def start(message: types.Message):
    await message.answer("欢迎使用定时消息机器人！\n命令：\n/add 添加定时")

@dp.message(commands=["add"])
async def add_schedule(message: types.Message, state: FSMContext):
    await message.answer("请发送一张图片或视频：")
    await state.set_state(ScheduleState.waiting_for_media)

@dp.message(ScheduleState.waiting_for_media, content_types=types.ContentType.ANY)
async def get_media(message: types.Message, state: FSMContext):
    if not (message.photo or message.video):
        return await message.answer("请发送图片或视频。")
    await state.update_data(media=message)
    await message.answer("请输入要发送的文字内容：")
    await state.set_state(ScheduleState.waiting_for_text)

@dp.message(ScheduleState.waiting_for_text)
async def get_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("是否添加按钮？请输入按钮文字，或输入 '无' 跳过：")
    await state.set_state(ScheduleState.waiting_for_button)

@dp.message(ScheduleState.waiting_for_button)
async def get_button(message: types.Message, state: FSMContext):
    button_text = message.text
    if button_text.lower() != "无":
        await state.update_data(button=button_text)
    else:
        await state.update_data(button=None)
    await message.answer("请输入发送间隔时间（单位：分钟）：")
    await state.set_state(ScheduleState.waiting_for_interval)

@dp.message(ScheduleState.waiting_for_interval)
async def get_interval(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("请输入有效的数字（分钟）：")
    await state.update_data(interval=int(message.text))
    await message.answer("请输入开始时间（格式：YYYY-MM-DD HH:MM）：")
    await state.set_state(ScheduleState.waiting_for_start_time)

@dp.message(ScheduleState.waiting_for_start_time)
async def get_start_time(message: types.Message, state: FSMContext):
    dt = parse_datetime(message.text)
    if not dt:
        return await message.answer("时间格式无效，请重新输入（YYYY-MM-DD HH:MM）：")
    await state.update_data(start_time=dt)
    await message.answer("请输入结束时间（格式：YYYY-MM-DD HH:MM）：")
    await state.set_state(ScheduleState.waiting_for_end_time)

@dp.message(ScheduleState.waiting_for_end_time)
async def get_end_time(message: types.Message, state: FSMContext):
    dt = parse_datetime(message.text)
    if not dt:
        return await message.answer("时间格式无效，请重新输入（YYYY-MM-DD HH:MM）：")
    await state.update_data(end_time=dt)
    data = await state.get_data()
    await message.answer(f"请确认以下信息：\n文字：{data['text']}\n按钮：{data.get('button', '无')}\n间隔：{data['interval']} 分钟\n开始时间：{data['start_time']}\n结束时间：{data['end_time']}\n输入 '确认' 发送，或 '取消' 放弃。")
    await state.set_state(ScheduleState.confirmation)

@dp.message(ScheduleState.confirmation)
async def confirm(message: types.Message, state: FSMContext):
    if message.text.lower() != "确认":
        await state.clear()
        return await message.answer("已取消。")
    data = await state.get_data()
    # 这里添加调度任务的逻辑
    schedule_message(chat_id=message.chat.id, data=data)
    add_task(message.chat.id, data)
    await message.answer("✅ 定时消息已设置。")
    await state.clear()