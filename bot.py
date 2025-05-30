from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from apscheduler.jobstores.base import JobLookupError

from scheduler import scheduler, schedule_message, remove_job
from database import add_task, get_all_tasks, delete_task

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# 状态管理
class ScheduleState(StatesGroup):
    waiting_for_time = State()
    waiting_for_message = State()

@dp.message(commands=["start"])
async def start(message: types.Message):
    await message.answer("欢迎使用定时消息机器人！\n命令：\n/add 添加定时\n/view 查看定时\n/delete 删除定时")

@dp.message(commands=["add"])
async def add_schedule(message: types.Message, state: FSMContext):
    await message.answer("请输入定时发送的时间（格式：YYYY-MM-DD HH:MM）")
    await state.set_state(ScheduleState.waiting_for_time)

@dp.message(ScheduleState.waiting_for_time)
async def get_time(message: types.Message, state: FSMContext):
    from utils import parse_datetime
    dt = parse_datetime(message.text)
    if not dt:
        return await message.answer("时间格式无效，请重新输入（YYYY-MM-DD HH:MM）")
    await state.update_data(scheduled_time=dt)
    await message.answer("请输入要发送的消息内容：")
    await state.set_state(ScheduleState.waiting_for_message)

@dp.message(ScheduleState.waiting_for_message)
async def get_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dt = data["scheduled_time"]
    msg = message.text

    job_id = f"{message.chat.id}-{dt.timestamp()}"
    schedule_message(chat_id=message.chat.id, text=msg, run_date=dt, job_id=job_id)
    add_task(message.chat.id, dt, msg, job_id)

    await message.answer(f"✅ 定时消息已设置：\n时间：{dt}\n内容：{msg}")
    await state.clear()

@dp.message(commands=["view"])
async def view_tasks(message: types.Message):
    tasks = get_all_tasks(message.chat.id)
    if not tasks:
        return await message.answer("暂无定时任务。")
    reply = "\n".join([f"{i+1}. ⏰ {row[1]} - {row[2]}\nID: {row[3]}" for i, row in enumerate(tasks)])
    await message.answer(f"已添加的任务：\n{reply}")

@dp.message(commands=["delete"])
async def delete_task_cmd(message: types.Message):
    await message.answer("请输入要删除的任务 ID（用 /view 命令查看）：")

@dp.message(lambda msg: msg.text.startswith("del_"))
async def delete_task_by_id(message: types.Message):
    job_id = message.text.replace("del_", "").strip()
    try:
        remove_job(job_id)
        delete_task(job_id)
        await message.answer(f"已删除任务：{job_id}")
    except JobLookupError:
        await message.answer("任务不存在或已执行完。")