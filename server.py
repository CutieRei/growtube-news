import asyncio
import fastapi
import importlib
import bot as bot_m

app = fastapi.FastAPI()
config = {
    "app": app,
    "bot": None
}

@app.on_event("startup")
async def startup():
    importlib.reload(bot_m)
    bot, token = bot_m.get_bot()
    config["bot"] = bot
    bot.config = config
    asyncio.create_task(bot.start(token))
    await bot.wait_until_ready()

@app.post("/restart")
async def restart(token: str):
    bot = config["bot"]
    if not token == bot.http.token:
        return {"status": 401, "msg": "Unauthorized"}
    await bot.close()
    await startup()
    return {"status": 200, "msg": "Ok"}

@app.get("/ping")
def ping():
    return {
        "msg": "PONG!"
    }
