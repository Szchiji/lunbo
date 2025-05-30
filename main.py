from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext
from app.states import MessageStates
from app.keyboards import confirm_keyboard
import sqlite3
from app.config import DATABASE_PATH

router = Router()

@router.message(F.photo | F.video)
async def handle_media(message: Message, state: FSMContext):
    if message.photo:
        await state.update_data(media_type="photo", media_file_id=message.photo[-1].file_id)
    elif message.video:
        await state.update_data(media_type="video", media_file_id=message.video.file_id)
    await message.answer("请输入文字内容：")
    await state.set_state(MessageStates.waiting_for_text)

@router.message(MessageStates.waiting_for_text)
async def handle_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("是否需要按钮？格式：文字-URL，多条请用逗号分隔，例如：官网-https://a.com, 投诉-https://b.com\n若无按钮请输入“无”")
    await state.set_state(MessageStates.waiting_for_buttons)

@router.message(MessageStates.waiting_for_buttons)
async def handle_buttons(message: Message, state: FSMContext):
    text = message.text
    await state.update_data(buttons=None if text.lower() == "无" else text)
    await message.answer("请输入发送间隔（秒）：")
    await state.set_state(MessageStates.waiting_for_interval)

@router.message(MessageStates.waiting_for_interval)
async def handle_interval(message: Message, state: FSMContext):
    await state.update_data(interval=int(message.text))
    await message.answer("请输入开始时间（格式：YYYY-MM-DD HH:MM）")
    await state.set_state(MessageStates.waiting_for_start_time)

@router.message(MessageStates.waiting_for_start_time)
async def handle_start_time(message: Message, state: FSMContext):
    await state.update_data(start_time=message.text)
    await message.answer("请输入结束时间（格式：YYYY-MM-DD HH:MM）")
    await state.set_state(MessageStates.waiting_for_end_time)

@router.message(MessageStates.waiting_for_end_time)
async def handle_end_time(message: Message, state: FSMContext):
    await state.update_data(end_time=message.text)
    data = await state.get_data()
    await message.answer_photo(
        data["media_file_id"] if data["media_type"] == "photo" else None,
        data["text"],
        reply_markup=confirm_keyboard()
    )
    await state.set_state(MessageStates.confirmation)

@router.callback_query(F.data.in_({"confirm", "cancel"}))
async def confirm_message(callback: CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await callback.message.answer("取消发布。")
        await state.clear()
        return
    data = await state.get_data()
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (user_id, media_type, media_file_id, text, buttons, interval, start_time, end_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        callback.from_user.id,
        data["media_type"],
        data["media_file_id"],
        data["text"],
        data["buttons"],
        data["interval"],
        data["start_time"],
        data["end_time"]
    ))
    conn.commit()
    conn.close()
    await callback.message.answer("消息已保存并将定时发送。")
    await state.clear()