from asyncio import gather
from bot import GrowTube, GrowContext, NotPermittedForPublish, MessagedError
from discord.ext import commands
from discord.ext.commands.errors import (
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
from io import BytesIO
import traceback
import discord

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
    async def on_command_error(self, ctx: GrowContext, error: commands.CommandError):
        error = getattr(error, "original", error)

        if ctx.command and ctx.command.has_error_handler():
            return

        if cog := ctx.cog:
            if cog.has_error_handler():
                return

        if isinstance(error, CommandNotFound):
            msg = ctx.message.content.replace(ctx.prefix, "").split()[0]
            await ctx.reply("No command named `{}`".format(msg))

        elif isinstance(error, CommandOnCooldown):
            await ctx.reply(
                "Please try again in {}".format(
                    precisedelta(timedelta(seconds=error.retry_after), format="%d")
                )
            )

        elif isinstance(error, MessagedError):
            await ctx.reply(str(error) or "Error occured")

        elif isinstance(error, _IGNORED_EXCEPTIONS):
            return

        else:
            tb = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            bot: commands.Bot = ctx.bot
            channel = bot.get_channel(ctx.bot.CHANNEL_LOG)
            tasks = [
                ctx.reply(
                    f"Oops an error has occured **{type(error).__name__}: {str(error)}**"
                )
            ]
            if channel:
                tasks.append(
                    channel.send(
                        "command: `{}`\nauthor: `{}`\nwhen: <t:{}:F>".format(
                            ctx.command.qualified_name,
                            ctx.author,
                            int(utcnow().timestamp()),
                        ),
                        file=discord.File(BytesIO(tb.encode()), "error.py"),
                    )
                )
            await gather(*tasks)


def setup(bot: GrowTube):
    bot.add_cog(ErrorHandler())
    bot.log.info(f"Loaded {__file__}")
