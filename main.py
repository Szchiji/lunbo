import asyncio
from aiohttp import web
from aiogram import types
from bot_init import dp, bot
import handlers  # noqa
from config import WEBHOOK_URL

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
app.router.add_post("/webhook", dp.webhook_handler)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8000)