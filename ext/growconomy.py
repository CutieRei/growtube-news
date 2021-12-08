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


def _calculate_price(base: int, demand: int, supply: int, d_units: int, s_units: int):
    try:
        return int(base * (demand + 1 * d_units) / (supply + 1 * s_units))
    except ZeroDivisionError:
        return base


class Growconomy(commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot

    async def cog_check(self, ctx: commands.Context[GrowTube]):
        _ignored_cmd = {"register", "market"}
        if await self.bot.pool.fetchrow(
            "SELECT 1 FROM users WHERE id=$1", ctx.author.id
        ):
            if ctx.command.name == "register":
                return False
            return True
        if ctx.command.name in _ignored_cmd:
            return await check(ctx)

    @commands.command(aliases=["bal", "balance"])
    async def bank(self, ctx: commands.Context):
        result = await self.bot.pool.fetchrow(
            "SELECT currency FROM users WHERE id = $1", ctx.author.id
        )
        embed = discord.Embed(
            title=f"{ctx.author} Account",
            description=f"**{currency_name}**: {result[0]:,}\n"
            f"**UserId**: {ctx.author.id}",
            color=discord.Colour.random(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def register(self, ctx: commands.Context):
        await self.bot.pool.execute("INSERT INTO users VALUES ($1, 0)", ctx.author.id)
        await ctx.reply("Registered!")

    @commands.command(aliases=["clt"])
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def collect(self, ctx: commands.Context):
        chance = randint(0, 100)
        if chance >= 60:
            item = 2
        elif chance >= 30:
            item = 1
        elif chance >= 0:
            item = 3
        item = await self.bot.pool.fetchrow(
            "SELECT name, id FROM items WHERE id=$1", item
        )
        if not await self.bot.pool.fetchrow(
            "SELECT 1 FROM inventory WHERE item_id=$1 AND user_id=$2",
            item[1],
            ctx.author.id,
        ):
            await self.bot.pool.execute(
                "INSERT INTO inventory VALUES ($1, $2)", item[1], ctx.author.id
            )
        else:
            await self.bot.pool.execute(
                "UPDATE inventory SET quantity = quantity + 1 WHERE item_id=$1 AND user_id=$2",
                item[1],
                ctx.author.id,
            )
        await ctx.reply(f"You found **{item[0]}** from the street")

    @commands.command(aliases=["inv"])
    async def inventory(self, ctx: commands.Context):
        records = await self.bot.pool.fetch(
            "SELECT items.name, inventory.quantity FROM inventory INNER JOIN items ON inventory.item_id=items.id WHERE user_id=$1",
            ctx.author.id,
        )
        records = [f"**{i[0].title()}[{i[1]}]**" for i in records]
        records = ", ".join(records) or "Empty...."
        await ctx.reply(records)

    @commands.command()
    async def sell(
        self,
        ctx: commands.Context,
        quantity: Optional[_quantity_convert] = 1,
        *,
        item_name,
    ):
        if quantity == 0:
            return
        record = await self.bot.pool.fetchrow(
            "SELECT inventory.item_id, inventory.quantity, items.value, items.name, items.supply, items.demand, items.stock FROM inventory INNER JOIN items ON items.id = inventory.item_id WHERE LOWER(items.name) = $1 AND user_id = $2",
            item_name.lower(),
            ctx.author.id,
        )
        if record is None:
            return
        value = record[2]
        if isinstance(quantity, str):
            quantity = record[1]
        remaining = record[1] - quantity
        if remaining < 0:
            return
        currency = _calculate_price(value, record[5], record[4], 0, record[6]) or 1
        currency *= quantity
        if record:
            async with self.bot.pool.acquire() as conn:
                async with conn.transaction():
                    if remaining == 0:
                        await conn.execute(
                            "DELETE FROM inventory WHERE user_id = $1 AND item_id = $2",
                            ctx.author.id,
                            record[0],
                        )
                    else:
                        await conn.execute(
                            "UPDATE inventory SET quantity = $1 WHERE user_id = $2 AND item_id = $3",
                            remaining,
                            ctx.author.id,
                            record[0],
                        )
                    await conn.execute(
                        "UPDATE items SET supply = supply + 1, stock = stock + $1 WHERE id = $2",
                        quantity,
                        record[0],
                    )
                    await conn.execute(
                        "UPDATE users SET currency = currency + $1 WHERE id = $2",
                        currency,
                        ctx.author.id,
                    )
            await ctx.send(
                f"Sold **{quantity}** {record[3]} for **{currency:,} {currency_name}**"
            )

    @commands.command()
    async def buy(
        self, ctx: commands.Context, quantity: Optional[int] = 1, *, item_name
    ):
        if quantity == 0:
            return
        record = await self.bot.pool.fetchrow(
            "SELECT items.id, items.value, items.name, items.supply, items.demand, items.stock FROM items WHERE LOWER(items.name) = $1",
            item_name.lower(),
        )
        if record is None:
            return
        if record[5] == 0:
            return await ctx.reply("Stock is empty....")
        currency = await self.bot.pool.fetchval(
            "SELECT currency FROM users WHERE id = $1", ctx.author.id
        )
        if record is None:
            return
        value = record[1]
        price = _calculate_price(value, record[4], record[3], quantity, record[5])
        price_total = price * quantity
        remaining = currency - price_total
        if remaining < 0:
            return
        if record:
            async with self.bot.pool.acquire() as conn:
                async with conn.transaction():
                    if await conn.fetchval(
                        "SELECT 1 FROM inventory WHERE item_id = $1 AND user_id = $2",
                        record[0],
                        ctx.author.id,
                    ):
                        await conn.execute(
                            "UPDATE inventory SET quantity = quantity + $1 WHERE user_id = $2 AND item_id = $3",
                            quantity,
                            ctx.author.id,
                            record[0],
                        )
                    else:
                        await conn.execute(
                            "INSERT INTO inventory VALUES ($1,$2,$3)",
                            record[0],
                            ctx.author.id,
                            quantity,
                        )
                    await conn.execute(
                        "UPDATE items SET demand = demand + 1, stock = stock - $1, supply = supply - 1 WHERE id = $2",
                        quantity,
                        record[0],
                    )
                    await conn.execute(
                        "UPDATE users SET currency = $1 WHERE id = $2",
                        remaining,
                        ctx.author.id,
                    )
            await ctx.send(
                f"Bought **{quantity}** {record[2]} for **{price_total:,} {currency_name}**"
            )

    @commands.command(aliases=["mkt", "ma"])
    async def market(self, ctx: commands.Context):
        """
        Format: (id)item name(price)(stock)
        """
        records = await self.bot.pool.fetch(
            "SELECT id, name, value, demand, supply, stock FROM items ORDER BY id ASC"
        )
        items = [
            f"[{record[0]}]{record[1]}({_calculate_price(record[2], record[3], record[4], 0, record[5])})({record[5]})"
            for record in records
        ]
        await ctx.send("```\n" + (", ".join(items)) + "\n```")

    @commands.command()
    async def top(self, ctx: commands.Context, limit: Optional[int] = 10):

        if limit > 30:
            limit = 30

        items = await self.bot.pool.fetch(
            "SELECT id, currency FROM users ORDER BY currency DESC LIMIT $1", limit
        )
        await ctx.reply(
            embed=discord.Embed(
                description="\n".join(
                    f"**#{index+1}** {self.bot.get_user(i[0])} __[{i[1]:,}]__"
                    for index, i in enumerate(items)
                )
            )
        )


def setup(bot: GrowTube) -> None:
    bot.add_cog(Growconomy(bot))
    bot.log.info(f"Loaded {__file__}")
