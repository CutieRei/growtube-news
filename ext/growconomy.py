from discord.colour import Color
from discord.ext import commands
from random import randint
from bot import GrowTube
from typing import NoReturn, Optional, Tuple, Union
import asyncpg
import discord

currency_name = "Growcoin"


async def check(ctx: commands.Context[GrowTube]) -> Union[bool, NoReturn]:
    result = await ctx.bot.pool.fetchrow(
        "SELECT * FROM beta_tester WHERE user_id=$1", ctx.author.id
    )
    return (result is not None) or (ctx.author.id in ctx.bot.owner_ids)

def _quantity_convert(arg):
    try:
        return int(arg)
    except ValueError:
        if arg.lower() == "all":
            return "all"
        raise


class Growconomy(commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot

    async def cog_check(self, ctx: commands.Context[GrowTube]):
        if await self.bot.pool.fetchrow("SELECT 1 FROM users WHERE id=$1", ctx.author.id):
            if ctx.command.name == "register":
                return False
            return True
        if ctx.command.name == "register":
            return await check(ctx)

    @commands.command(aliases=["bal", "balance"])
    async def bank(self, ctx: commands.Context):
        result = await self.bot.pool.fetchrow("SELECT currency FROM users WHERE id = $1", ctx.author.id)
        embed = discord.Embed(
            title=f"{ctx.author} Account",
            description=f"**{currency_name}**: {result[0]}\n"
            f"**UserId**: {ctx.author.id}",
            color=discord.Colour.random(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def register(self, ctx: commands.Context):
        await self.bot.pool.execute(
            "INSERT INTO users VALUES ($1, 0)", ctx.author.id
        )
        await ctx.reply("Registered!")

    @commands.command(aliases=["clt"])
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def collect(self, ctx: commands.Context):
        chance = randint(0,100)
        if chance >= 60:
            item = 2
        elif chance >= 30:
            item = 1
        elif chance >= 0:
            item = 3
        item = await self.bot.pool.fetchrow("SELECT name, id FROM items WHERE id=$1", item)
        if not await self.bot.pool.fetchrow("SELECT 1 FROM inventory WHERE item_id=$1 AND user_id=$2", item[1], ctx.author.id):
            await self.bot.pool.execute("INSERT INTO inventory VALUES ($1, $2)", item[1], ctx.author.id)
        else:
            await self.bot.pool.execute("UPDATE inventory SET quantity = quantity + 1 WHERE item_id=$1 AND user_id=$2", item[1], ctx.author.id)
        await ctx.reply(f"You found **{item[0]}** from the street")

    @commands.command(aliases=["inv"])
    async def inventory(self, ctx: commands.Context):
        records = await self.bot.pool.fetch("SELECT items.name, inventory.quantity FROM inventory INNER JOIN items ON inventory.item_id=items.id WHERE user_id=$1", ctx.author.id)
        records = [f"**{i[0].title()}[{i[1]}]**" for i in records]
        records = ", ".join(records) or "Empty...."
        await ctx.reply(records)

    @commands.command()
    async def sell(self, ctx: commands.Context, quantity: Optional[_quantity_convert] = 1, *, item_name):
        """
        50% tax for sold items
        """
        if quantity == 0:
            return
        record = await self.bot.pool.fetchrow("SELECT inventory.item_id, inventory.quantity, items.value, items.name FROM inventory INNER JOIN items ON items.id = inventory.item_id WHERE LOWER(items.name) = $1 AND user_id = $2", item_name.lower(), ctx.author.id)
        if record is None:
            return
        value = record[2]
        if isinstance(quantity, str):
            quantity = record[1]
        remaining = record[1] - quantity
        if remaining < 0:
            return
        currency = (quantity*value)//2
        if record:
            if remaining == 0:
                await self.bot.pool.execute("DELETE FROM inventory WHERE user_id = $1 AND item_id = $2", ctx.author.id, record[0])
            else:
                await self.bot.pool.execute("UPDATE inventory SET quantity = $1 WHERE user_id = $2 AND item_id = $3", remaining, ctx.author.id, record[0])
            await self.bot.pool.execute("UPDATE users SET currency = currency + $1 WHERE id = $2", currency, ctx.author.id)
            await ctx.send(f"Sold **{quantity}** {record[3]} for **{currency} {currency_name}** with 50% tax")

def setup(bot: GrowTube) -> None:
    bot.add_cog(Growconomy(bot))
    bot.log.info(f"Loaded {__file__}")
