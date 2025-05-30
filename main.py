from fastapi import FastAPI, Request
from aiogram import types
from app.bot import bot, dp
from app.config import WEBHOOK_PATH

app = FastAPI()

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    update = types.Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}