from fastapi import FastAPI, Request
import asyncio
from bot import dp, bot
from config import WEBHOOK_PATH, WEBHOOK_URL

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    update = await request.json()
    await dp.feed_update(bot, update)
    return {"ok": True}