from discord.colour import Color
from discord.ext import commands
from random import choices
from bot import GrowTube
from discord.utils import utcnow
from typing import NoReturn, Optional, Tuple, Union
from .trading import Trading
import asyncpg
import discord

currency_name = "Growcoin"
embed_color = GrowTube.EMBED_COLOUR
currency_emoji = "<:growcoin:918403481419788349>"


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


class Growconomy(Trading, commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot
        super().__init__()

    async def cog_check(self, ctx: commands.Context[GrowTube]):
        _ignored_cmd = {self.register, self.market}
        if await self.bot.pool.fetchrow(
            "SELECT 1 FROM users WHERE id=$1", ctx.author.id
        ):
            if ctx.command == self.register:
                return False
            return True
        if ctx.command in _ignored_cmd:
            return await check(ctx)

    @commands.command(aliases=["bal", "balance"])
    async def bank(self, ctx: commands.Context, user: discord.User = None):
        user = user or ctx.author
        result = await self.bot.pool.fetchrow(
            "SELECT currency FROM users WHERE id = $1", user.id
        )
        if result is None:
            raise commands.CommandError("this user does not have an account")
        embed = discord.Embed(
            title=f"{user} Account",
            description=f"**{currency_name}**: {result[0]:,} {currency_emoji}",
            color=embed_color,
            timestamp=utcnow(),
        )
        embed.set_thumbnail(url=user.avatar.url)
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.me.display_avatar.url
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def register(self, ctx: commands.Context):
        await self.bot.pool.execute("INSERT INTO users VALUES ($1, 0)", ctx.author.id)
        await ctx.reply("Registered!")

    @commands.command(aliases=["clt"])
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def collect(self, ctx: commands.Context):
        item = choices([1, 2, 3, 4, 5, 6], [50, 45, 30, 50, 15, 15])[0]
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
            "SELECT items.name, inventory.quantity, items.demand, items.supply, items.stock, items.value FROM inventory INNER JOIN items ON inventory.item_id=items.id WHERE user_id=$1 ORDER BY inventory.quantity DESC",
            ctx.author.id,
        )
        items = []
        summed = []
        for record in records:
            price = (
                _calculate_price(record[5], record[2], record[3], 0, record[4])
                * record[1]
            )
            summed.append(price)
            items.append(
                f"{record[0].title()}: {record[1]:,} | Estimated Value: {price:,}"
            )
        if summed:
            items.append(f"\nEstimated Total Values: {sum(summed):,}")
        records = "\n".join(items) or "Empty...."
        await ctx.reply("```\n" + records + "```")

    @commands.command()
    async def sell(
        self,
        ctx: commands.Context,
        quantity: Optional[_quantity_convert] = 1,
        *,
        item_name,
    ):
        if quantity != "all" and quantity <= 0:
            return
        record = await self.bot.pool.fetchrow(
            "SELECT inventory.item_id, inventory.quantity, items.value, items.name, items.supply, items.demand, items.stock FROM inventory INNER JOIN items ON items.id = inventory.item_id WHERE LOWER(items.name) = $1 AND user_id = $2",
            item_name.lower(),
            ctx.author.id,
        )
        if record is None:
            return
        value = record[2]
        if quantity == "all":
            quantity = record[1]
        remaining = record[1] - quantity
        if remaining < 0:
            return
        currency = _calculate_price(value, record[5], record[4], 0, record[6])
        if currency < 0:
            currency = 0
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
                f"Sold **{quantity}** {record[3]} for **{currency:,} {currency_name}** {currency_emoji}"
            )

    @commands.command()
    async def buy(
        self, ctx: commands.Context, quantity: Optional[int] = 1, *, item_name
    ):
        if quantity <= 0:
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
        price = _calculate_price(value, record[4], record[3], 0, record[5])
        if price < 0:
            price = 1
        price_total = price * quantity
        remaining = currency - price_total
        if remaining < 0 or (record[5] - quantity) < 0:
            return
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
                    "UPDATE items SET demand = demand + 1, stock = stock - $1 WHERE id = $2 AND stock > 0",
                    quantity,
                    record[0],
                )
                await conn.execute(
                    "UPDATE users SET currency = $1 WHERE id = $2",
                    remaining,
                    ctx.author.id,
                )
            await ctx.send(
                f"Bought **{quantity}** {record[2]} for **{price_total:,} {currency_name}** {currency_emoji}"
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
        await ctx.send("```\n" + ("\n".join(items)) + "\n```")

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
                    f"**#{index+1}** {self.bot.get_user(i[0])}: __{i[1]:,}__ {currency_emoji}"
                    for index, i in enumerate(items)
                ),
                color=embed_color,
            )
        )

    @commands.command()
    async def transfer(self, ctx: commands.Context, user: discord.User, amount: int):
        async with self.bot.pool.acquire() as conn:
            record = await conn.fetchval("SELECT 1 FROM users WHERE id = $1", user.id)
            if not record:
                return
            currency = await conn.fetchval(
                "SELECT currency FROM users WHERE id = $1", ctx.author.id
            )
            if amount > currency:
                return
            await conn.execute(
                "UPDATE users SET currency = currency + $1 WHERE id = $2",
                amount,
                user.id,
            )
            await conn.execute(
                "UPDATE users SET currency = currency - $1 WHERE id = $2",
                amount,
                ctx.author.id,
            )
            await ctx.send(f"Transfered **{amount:,}** {currency_emoji} to **{user}**")

