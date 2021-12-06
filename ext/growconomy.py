from discord.colour import Color
from discord.ext import commands
from bot import GrowTube
from typing import NoReturn, Optional, Tuple, Union
import asyncpg
import discord

currency_name = "Growcoin"


async def check(ctx: commands.Context[GrowTube]) -> Union[bool, NoReturn]:
    result = await ctx.bot.pool.fetchrow(
        "SELECT * FROM beta_tester WHERE user_id=$1", ctx.author.id
    )
    return result or ctx.author.id in ctx.bot.owner_ids


class Groconomy(commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot

    @commands.command()
    @commands.check(check)
    async def bank(self, ctx: commands.Context):
        result: Optional[Tuple[int, int]] = await self.bot.pool.fetchrow(
            "SELECT currency FROM users WHERE id=$1", ctx.author.id
        )
        if result is None:
            return
        embed = discord.Embed(
            title=f"{ctx.author} Account",
            description=f"**{currency_name}**: {result[0]}\n"
            f"**UserId**: {ctx.author.id}",
            color=discord.Colour.random(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def register(self, ctx: commands.Context):
        try:
            await self.bot.pool.execute(
                "INSERT INTO users VALUES ($1, 0)", ctx.author.id
            )
            await ctx.reply("Registered!")
        except asyncpg.exceptions.UniqueViolationError:
            pass


def setup(bot: GrowTube) -> None:
    bot.add_cog(Groconomy(bot))
    bot.log.info(f"Loaded {__file__}")
