from bot import GrowTube
from discord.ext import commands
from typing import Dict, List, Optional
from discord import User


class Trading:
    bot: GrowTube

    def __init__(self):
        self.users: Dict[int, str] = {}
        self.trades: Dict[str, Dict[int, List]] = {}

    @commands.group()
    async def trade(self, ctx, user: Optional[User] = None):
        if not ctx.invoked_subcommand:
            if not user:
                return
            elif ctx.author == user:
                await ctx.reply("You can't trade with yourself dummy")
            elif ctx.author.id in self.users:
                await ctx.reply("You're already in a trade")
            elif user.id in self.users:
                await ctx.reply(f"**{user}** is already in a trade")
            elif not await self.bot.pool.fetchval(
                "SELECT 1 FROM users WHERE id = $1", user.id
            ):
                await ctx.reply("User is not registered")
        elif ctx.author.id not in self.users:
            await ctx.reply("You're not in a trade")

    @trade.command()
    async def add(self, ctx):
        return
