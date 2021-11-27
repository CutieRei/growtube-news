from bot import GrowTube, NotPermittedForPublish
from discord.ext import commands
from discord.ext.commands.errors import (
    CommandNotFound,
    MissingRequiredArgument,
    NoPrivateMessage,
)
import traceback
import datetime


class ErrorHandler(commands.Cog):
    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        error = getattr(error, "original", error)

        if ctx.command.has_error_handler():
            return

        if cog := ctx.cog:
            if cog.has_error_handler():
                return

        if isinstance(error, MissingRequiredArgument):
            error: MissingRequiredArgument
            await ctx.send(f"Missing required argument {error.param}")

        elif isinstance(error, CommandNotFound):
            error: CommandNotFound
            msg = ctx.message.content.replace(ctx.prefix, "")
            await ctx.send("No command named `{}`".format(msg))

        elif isinstance(error, (NoPrivateMessage, NotPermittedForPublish)):
            return

        else:
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            bot: commands.Bot = ctx.bot
            channel = bot.get_channel(ctx.bot.CHANNEL_LOG)
            if channel:
                return await channel.send(
                    "command: `{}`\nauthor: `{}`\nwhen: <t:{}:F>\n```py\n{}```".format(
                        ctx.command.qualified_name,
                        ctx.author,
                        int(datetime.datetime.utcnow().timestamp()),
                        "".join(tb),
                    )
                )


def setup(bot: GrowTube):
    bot.add_cog(ErrorHandler())
    print(f"Loaded {__name__}")
