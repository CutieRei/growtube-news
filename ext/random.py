from typing import Optional
from discord.ext import commands
from bot import GrowTube
import random
import discord


class Random(commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot

    @commands.command(usage="<things...>")
    async def pick(self, ctx: commands.Context, *things: str):
        await ctx.send(
            random.choice(things), allowed_mentions=discord.AllowedMentions.none()
        )

    @commands.command(aliases=["pfp", "av", "profile"])
    async def avatar(self, ctx: commands.Context, who: Optional[discord.Member] = None):
        who = who or ctx.author
        embed = discord.Embed(
            title=f"Avatar for {who}", url=who.avatar.url, color=who.color
        )
        embed.set_image(url=who.avatar.url)
        await ctx.send(embed=embed)


def setup(bot: GrowTube) -> None:
    bot.add_cog(Random(bot))
    bot.log.info(f"Loaded {__file__}")
