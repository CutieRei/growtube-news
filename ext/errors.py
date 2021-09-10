from bot import NotPermittedForPublish
from discord.ext import commands
from discord.ext.commands.errors import CommandNotFound, MissingRequiredArgument, NoPrivateMessage
import traceback
import datetime

CHANNEL_LOG = 883936874400452619

class ErrorHandler(commands.Cog):

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        error = getattr(error, "original", error)

        if hasattr(ctx.command, "on_error"):
            return
        
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return
        
        if isinstance(error, MissingRequiredArgument):
            error: MissingRequiredArgument
            await ctx.send(f"Missing required argument {error.param}")
        
        elif isinstance(error, CommandNotFound):
            error: CommandNotFound
            await ctx.send("No command named `{}`".format(ctx.message.content.replace(ctx.prefix, "")))
        
        elif isinstance(error, (NoPrivateMessage, NotPermittedForPublish)):
            return
        
        else:
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            bot: commands.Bot = ctx.bot
            channel = bot.get_channel(CHANNEL_LOG)
            if channel:
                return await channel.send("command: `{}`\nauthor: `{}`\nwhen: <t:{}:F>\n```py\n{}```".format(ctx.command.qualified_name, ctx.author, int(datetime.datetime.utcnow().timestamp()), "".join(tb)))


def setup(bot):
    bot.add_cog(ErrorHandler())
