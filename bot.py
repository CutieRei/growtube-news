import storage
from discord.ext import commands
import os
import json
from asyncio import gather

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
        await gather(self.db.close(), super().close())

class NotPermittedForPublish(commands.CheckFailure):
    pass

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
        
    return bot, token

if __name__ == "__main__":
    bot, token = get_bot()
    bot.run(token)