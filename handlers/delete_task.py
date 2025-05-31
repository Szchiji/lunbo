from aiogram import types
from aiogram.types import Message

async def delete_task(message: Message):
    await message.answer("删除任务的功能还未实现（请根据任务 ID 删除数据库记录）")
