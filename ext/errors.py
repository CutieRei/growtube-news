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
    CommandOnCooldown,
)
from discord.utils import utcnow
from datetime import timedelta
from humanize import precisedelta
import traceback

_IGNORED_EXCEPTIONS = (
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

        if ctx.command and ctx.command.has_error_handler():
            return

        if cog := ctx.cog:
            if cog.has_error_handler():
                return

        if isinstance(error, CommandNotFound):
            msg = ctx.message.content.replace(ctx.prefix, "")
            await ctx.reply("No command named `{}`".format(msg))

        elif isinstance(error, CommandOnCooldown):
            await ctx.reply(
                "Please try again in {}".format(
                    precisedelta(timedelta(seconds=error.retry_after), format="%d")
                )
            )

        elif isinstance(error, _IGNORED_EXCEPTIONS):
            return

        else:
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            bot: commands.Bot = ctx.bot
            channel = bot.get_channel(ctx.bot.CHANNEL_LOG)
            tasks = []
            if channel:
                tasks.append(
                    channel.send(
                        "command: `{}`\nauthor: `{}`\nwhen: <t:{}:F>\n```py\n{}```".format(
                            ctx.command.qualified_name,
                            ctx.author,
                            int(utcnow().timestamp()),
                            "".join(tb),
                        )
                    )
                )
            if ctx.author.id in ctx.bot.owner_ids:
                tasks.append(ctx.message.add_reaction("\U0000203c"))
            return await gather(*tasks)


def setup(bot: GrowTube):
    bot.add_cog(ErrorHandler())
    bot.log.info(f"Loaded {__file__}")
