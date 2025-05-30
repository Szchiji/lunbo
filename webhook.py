from config import WEBHOOK_URL
from bot_init import bot

async def setup_webhook():
    await bot.set_webhook(WEBHOOK_URL)