from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ 确认", callback_data="confirm")],
            [InlineKeyboardButton(text="❌ 取消", callback_data="cancel")]
        ]
    )