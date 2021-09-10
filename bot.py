import storage
from discord.ext import commands
import os
import json
import asyncio

class DB(storage.MockAsyncReplitStorage):

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._items.update(
            {
                "0": {},
                "1": {},
                "2": {}
            }
        )

class GrowTube(commands.Bot):

    db: storage.AsyncReplitStorage

    def __init__(self, command_prefix, help_command=None, description=None, **options):
        super().__init__(command_prefix, help_command=help_command, description=description, **options)
        self.db = DB()
    
    async def close(self):
        await asyncio.gather(self.db.close(), super().close())

class NotPermittedForPublish(commands.CheckFailure):
    pass

class CommandNotFound(Exception):

    def __init__(self, obj, msg = "Command not found"):
        self.msg = msg
        self.obj = obj

    def __str__(self):
        return self.msg 

def get_bot():
    
    config = None
    with open("config.json") as f:
        config = json.load(f)
    
    token = os.getenv("TOKEN")

    if not token:
        import dotenv
        dotenv.load_dotenv()
        token = os.getenv("TOKEN")

    bot = GrowTube(
        command_prefix = config["prefix"],
        owner_ids = config["owners"]
    )

    for extension in config["ext"]:
        try:
            bot.load_extension(config["ext_dir"]+"."+extension)
        except Exception:
            pass

    if config["debug"]:
        bot.load_extension("jishaku")

    @bot.listen()
    async def on_ready():
        print("Logged in")

    import aiohttp

    async def _job():
        async with aiohttp.ClientSession() as sess:
            await sess.post("http://localhost:8000/restart", params={"token": bot.http.token})

    @bot.command()
    @commands.is_owner()
    async def restart(ctx):
        await ctx.message.add_reaction("\U00002705")
        asyncio.create_task(_job())
        
    return bot, token

if __name__ == "__main__":
    bot, token = get_bot()
    bot.run(token)
