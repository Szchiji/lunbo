from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .bot import dp
from .scheduler import schedule_message
from .utils import parse_datetime

class ScheduleState(StatesGroup):
    waiting_for_media = State()
    waiting_for_text = State()
    waiting_for_buttons = State()
    waiting_for_interval = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    confirmation = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("欢迎使用定时消息机器人！发送 /add 开始设置定时消息。")

@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    await message.answer("请发送一张图片或视频：")
    await state.set_state(ScheduleState.waiting_for_media)

@dp.message(ScheduleState.waiting_for_media)
async def handle_media(message: types.Message, state: FSMContext):
    if not (message.photo or message.video):
        await message.answer("请发送一张图片或视频。")
        return
    await state.update_data(media=message)
    await message.answer("请输入要发送的文字内容：")
    await state.set_state(ScheduleState.waiting_for_text)

@dp.message(ScheduleState.waiting_for_text)
async def handle_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("是否添加按钮？格式：按钮文本1,按钮文本2（如无，发送 '无'）：")
    await state.set_state(ScheduleState.waiting_for_buttons)

@dp.message(ScheduleState.waiting_for_buttons)
async def handle_buttons(message: types.Message, state: FSMContext):
    buttons = message.text
    await state.update_data(buttons=buttons if buttons.lower() != "无" else None)
    await message.answer("请输入发送间隔时间（单位：分钟）：")
    await state.set_state(ScheduleState.waiting_for_interval)

@dp.message(ScheduleState.waiting_for_interval)
async def handle_interval(message: types.Message, state: FSMContext):
    try:
        interval = int(message.text)
        await state.update_data(interval=interval)
        await message.answer("请输入开始时间（格式：YYYY-MM-DD HH:MM）：")
        await state.set_state(ScheduleState.waiting_for_start_time)
    except ValueError:
        await message.answer("请输入有效的数字作为间隔时间。")

@dp.message(ScheduleState.waiting_for_start_time)
async def handle_start_time(message: types.Message, state: FSMContext):
    start_time = parse_datetime(message.text)
    if not start_time:
        await message.answer("时间格式无效，请重新输入（格式：YYYY-MM-DD HH:MM）：")
        return
    await state.update_data(start_time=start_time)
    await message.answer("请输入结束时间（格式：YYYY-MM-DD HH:MM）：")
    await state.set_state(ScheduleState.waiting_for_end_time)

@dp.message(ScheduleState.waiting_for_end_time)
async def handle_end_time(message: types.Message, state: FSMContext):
    end_time = parse_datetime(message.text)
    if not end_time:
        await message.answer("时间格式无效，请重新输入（格式：YYYY-MM-DD HH:MM）：")
        return
    await state.update_data(end_time=end_time)
    data = await state.get_data()
    await message.answer(f"""请确认以下信息：
媒体类型：{'图片' if data['media'].photo else '视频'}
文字内容：{data['text']}
按钮：{data['buttons'] or '无'}
间隔时间：{data['interval']} 分钟
开始时间：{data['start_time']}
结束时间：{end_time}
确认发送请回复 '确认'，取消请回复 '取消'。""")
    await state.set_state(ScheduleState.confirmation)

@dp.message(ScheduleState.confirmation)
async def handle_confirmation(message: types.Message, state: FSMContext):
    if message.text.lower() == "确认":
        data = await state.get_data()
        # 调用调度函数 schedule_message，传入相关参数
        await schedule_message(data)
        await message.answer("定时消息已设置成功！")
    else:
        await message.answer("已取消设置。")
    await state.clear()