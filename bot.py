import aiohttp
import storage
import os
import json
import asyncio
import traceback
from discord.ext import commands

class GrowTube(commands.Bot):

    CHANNEL_LOG = 883936874400452619

    def __init__(self, command_prefix, help_command=None, description=None, **options):
        super().__init__(command_prefix, help_command=help_command, description=description, **options)
        self.db = storage.PostgresStorage(options.pop("dsn"))
     
    async def start(self, *args, **kwargs):
        await self.db
        self.http_session = aiohttp.ClientSession()
        await super().start(*args, **kwargs)
    
    async def close(self):
        await asyncio.gather(self.db.close(), self.http_session.close(), super().close())

class NotPermittedForPublish(commands.CheckFailure):
    pass

def get_bot():
    
    config = None
    config_file = "config.json" if os.path.isfile("config.json") else "default-config.json"
    with open(config_file) as f:
        config = json.load(f)
    
    token = os.getenv("TOKEN")

    if not token:
        import dotenv
        dotenv.load_dotenv()
        token = os.getenv("TOKEN")

    bot = GrowTube(
        command_prefix = config["prefix"],
        owner_ids = config["owners"],
        dsn = config["dsn"]
    )

    async def _ext_err(e: Exception):
        await bot.wait_until_ready()
        exc = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        channel = bot.get_channel(bot.CHANNEL_LOG)
        if channel:
            await channel.send(f"```py\n{exc}\n```")

    for extension in config["ext"]:
        try:
            bot.load_extension(config["ext_dir"]+"."+extension)
        except Exception as exc:
            asyncio.create_task(_ext_err(exc))

    if config["debug"]:
        bot.load_extension("jishaku")

    @bot.listen()
    async def on_ready():
        print("Logged in")

    import aiohttp

    async def _job():
        async with aiohttp.ClientSession() as sess:
            await sess.post("http://localhost:8000/restart", data={"token": bot.http.token})

    @bot.command()
    @commands.is_owner()
    async def restart(ctx):
        await ctx.message.add_reaction("\U00002705")
        asyncio.create_task(_job())
        
    return bot, token

if __name__ == "__main__":
    bot, token = get_bot()
    #bot.run(token)
