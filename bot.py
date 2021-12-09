from discord.ext import commands
from discord.utils import utcnow
import aiohttp
import asyncpg
import discord
import logs
import logging
import storage
import os
import json
import asyncio
import traceback
import psutil

psutil.cpu_percent()


class GrowTube(commands.Bot):
    EMBED_COLOUR = discord.Color(15007744)

    def __init__(self, command_prefix, help_command=None, description=None, **options):
        super().__init__(
            command_prefix,
            help_command=help_command,
            description=description,
            **options,
        )
        debug = options.pop("debug", False)
        sh = logs.ClickStreamHandler()
        sh.setFormatter(
            logs.ColouredFormatter(
                "[%(levelname)s][%(filename)s] %(message)s",
                use_colours=options.pop("use_colour", True),
            )
        )
        self.pool = asyncpg.create_pool(options.pop("dsn"))
        self.db = storage.PostgresStorage(self.pool)
        self.CHANNEL_LOG = options.pop("channel_log", None)
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG if debug else logging.INFO)
        self.log.addHandler(sh)

    async def start(self, *args, **kwargs):
        await self.pool
        self.http_session = aiohttp.ClientSession()
        self.uptime = utcnow()
        await super().start(*args, **kwargs)

    async def close(self):
        self.log.info("Logging out now")
        results = await asyncio.gather(
            self.pool.close(),
            self.http_session.close(),
            super().close(),
            return_exceptions=True,
        )
        for res in results:
            if isinstance(res, BaseException):
                self.log.exception(
                    "A coroutine raised an error while handling close", exc_info=res
                )
        self.log.info("Bot closed")


class NotPermittedForPublish(commands.CheckFailure):
    pass


def get_bot(use_colour: bool = True):

    config = None
    config_file = (
        "config.json" if os.path.isfile("config.json") else "default-config.json"
    )
    with open(config_file) as f:
        config = json.load(f)

    token = os.getenv("TOKEN")

    if not token:
        import dotenv

        dotenv.load_dotenv()
        token = os.getenv("TOKEN")

    intents = discord.Intents.default()
    intents.members = True
    bot = GrowTube(
        command_prefix=config["prefix"],
        owner_ids=config["owners"],
        dsn=config["dsn"],
        channel_log=config["channel_log"],
        debug=config.get("debug", False),
        use_colour=use_colour,
        intents=intents,
    )

    async def _ext_err(e: Exception):
        await bot.wait_until_ready()
        exc = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        channel = bot.get_channel(bot.CHANNEL_LOG)
        if channel:
            await channel.send(f"```py\n{exc}\n```")

    for extension in config["ext"]:
        try:
            bot.load_extension(config["ext_dir"] + "." + extension)
        except Exception as exc:
            asyncio.create_task(_ext_err(exc))

    bot.load_extension("jishaku")

    @bot.listen()
    async def on_ready():
        bot.log.info("Logged in")

    return bot, token


if __name__ == "__main__":
    bot, token = get_bot()
    bot.run(token)
