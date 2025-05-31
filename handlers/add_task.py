from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import AddTaskState
from database import add_task
import os

router = Router()

@router.message(F.text == "/addtask")
async def start_add(message: Message, state: FSMContext):
    await message.answer("请发送图片或视频")
    await state.set_state(AddTaskState.waiting_for_media)

@router.message(AddTaskState.waiting_for_media, F.photo | F.video)
async def receive_media(message: Message, state: FSMContext):
    media_type = "photo" if message.photo else "video"
    file = message.photo[-1] if message.photo else message.video
    file_path = f"media/{file.file_id}.jpg"
    await message.bot.download(file, destination=file_path)
    await state.update_data(media_type=media_type, media_path=file_path, chat_id=message.chat.id)
    await message.answer("请输入文字说明")
    await state.set_state(AddTaskState.waiting_for_caption)

# 后续状态处理略，完整版本可继续添加
