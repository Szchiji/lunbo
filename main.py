import uvicorn
from fastapi import FastAPI, Request
from aiogram.types import Update
from bot_init import dp, bot
from handlers import router
from webhook import setup_webhook

app = FastAPI()

dp.include_router(router)

@app.on_event("startup")
async def on_startup():
    await setup_webhook()

@app.post("/webhook")
async def webhook_handler(request: Request):
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)