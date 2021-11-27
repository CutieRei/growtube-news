from asyncio import gather
from bot import GrowTube, NotPermittedForPublish
from discord.ext import commands
from discord.ext.commands.errors import (
    BotMissingRole,
    CommandNotFound,
    ConversionError,
    MissingAnyRole,
    MissingPermissions,
    MissingRequiredArgument,
    MissingRole,
    NoPrivateMessage,
    NotOwner,
)
import traceback
import datetime

_IGNORED_EXCEPTIONS = (
    CommandNotFound,
    NoPrivateMessage,
    NotPermittedForPublish,
    NotOwner,
    MissingRequiredArgument,
    MissingRole,
    MissingAnyRole,
    MissingPermissions,
    ConversionError,
)


class ErrorHandler(commands.Cog):
    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context[GrowTube], error: commands.CommandError
    ):
        error = getattr(error, "original", error)

        if ctx.command.has_error_handler():
            return

        if cog := ctx.cog:
            if cog.has_error_handler():
                return

        elif isinstance(error, CommandNotFound):
            msg = ctx.message.content.replace(ctx.prefix, "")
            await ctx.send("No command named `{}`".format(msg))

        elif isinstance(error, _IGNORED_EXCEPTIONS):
            return

        else:
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            bot: commands.Bot = ctx.bot
            channel = bot.get_channel(ctx.bot.CHANNEL_LOG)
            if channel:
                tasks = [
                    channel.send(
                        "command: `{}`\nauthor: `{}`\nwhen: <t:{}:F>\n```py\n{}```".format(
                            ctx.command.qualified_name,
                            ctx.author,
                            int(datetime.datetime.utcnow().timestamp()),
                            "".join(tb),
                        )
                    )
                ]
                if ctx.author in ctx.bot.owner_ids:
                    tasks.append(ctx.message.add_reaction("\U0000203c"))
                return await gather(tasks)


def setup(bot: GrowTube):
    bot.add_cog(ErrorHandler())
    bot.log.info(f"Loaded {__file__}")
