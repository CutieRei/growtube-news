import aiohttp
import logs
import logging
import storage
import os
import json
import asyncio
import traceback
import humanize
from discord.ext import commands
from datetime import datetime


class GrowTube(commands.Bot):
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
        self.db = storage.PostgresStorage(options.pop("dsn"))
        self.CHANNEL_LOG = options.pop("channel_log", None)
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG if debug else logging.INFO)
        self.log.addHandler(sh)

    async def start(self, *args, **kwargs):
        await self.db
        self.http_session = aiohttp.ClientSession()
        self.uptime = datetime.utcnow()
        await super().start(*args, **kwargs)

    async def close(self):
        self.log.info("Logging out now")
        results = await asyncio.gather(
            self.db.close(), self.http_session.close(), super().close(), return_exceptions=True
        )
        for res in results:
            if isinstance(res, BaseException):
                self.log.exception("A coroutine raised an error while handling close", exc_info=res)
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

    bot = GrowTube(
        command_prefix=config["prefix"],
        owner_ids=config["owners"],
        dsn=config["dsn"],
        channel_log=config["channel_log"],
        debug=config.get("debug", False),
        use_colour=use_colour,
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

    if config["debug"]:
        bot.load_extension("jishaku")

    @bot.listen()
    async def on_ready():
        bot.log.info("Logged in")

    @bot.command()
    async def uptime(ctx):
        time = datetime.utcnow() - bot.uptime
        await ctx.send(f"Bot has been up for **{humanize.precisedelta(time)}**")

    return bot, token


if __name__ == "__main__":
    bot, token = get_bot()
    bot.run(token)
