import asyncio
import fastapi
from bot import get_bot

app = fastapi.FastAPI()
config = {
    "app": app
}

@app.on_event("startup")
async def startup():
    bot, token = get_bot()
    bot.config = config
    asyncio.create_task(bot.start(token))
    await bot.wait_until_ready()

@app.get("/ping")
def ping():
    return {
        "msg": "PONG!"
    }