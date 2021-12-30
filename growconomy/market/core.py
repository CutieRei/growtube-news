from discord.ext import commands
from random import choices
from asyncio import create_task
from bot import GrowContext, MessagedError
from discord.utils import utcnow
from typing import Optional, Union, Literal
from ..constants import currency_emoji, currency_name, embed_color, GrowTube
from ..trading import Trading
import discord
import json

big_tax = 3
small_tax = 2

def compute_transaction(amount: int):
    if amount > 100000:
        return int(amount + (amount * big_tax//100)), big_tax
    return int(amount + (amount * small_tax//100)), small_tax


def _quantity_convert(arg) -> Union[int, Literal["all"]]:
    try:
        return int(arg)
    except ValueError:
        if arg.lower() == "all":
            return "all"
        raise MessagedError(f"unknown value `{arg}`")


def _trade_check(ctx: GrowContext):
    cog: Optional[Trading] = ctx.bot.get_cog("Trading")
    if cog is None:
        return True
    session = cog.users.get(ctx.author.id)
    if session:
        if session.id in cog.trades:
            raise MessagedError("You're currently trading")
    return True


def _calculate_price(base: int, demand: int, supply: int, d_units: int, s_units: int):
    try:
        return int(base * (demand + 1 * d_units) / (supply + 1 * s_units))
    except ZeroDivisionError:
        return base


class Market(commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot
        self.news: Optional[str] = None

    async def cog_check(self, ctx: GrowContext):
        _ignored_cmd = {self.market, self.top, self.news}
        if ctx.command in _ignored_cmd:
            return True
        elif await self.bot.pool.fetchval(
            "SELECT 1 FROM users WHERE id=$1", ctx.author.id
        ):
            if ctx.command == self.register:
                raise MessagedError("You're already registered")
            return True
        raise MessagedError("You're not registered")
    
    @commands.group(invoke_without_command=True)
    async def news(self, ctx: GrowContext):
        await ctx.reply(self.news or "No news")
    
    @news.command()
    @commands.is_owner()
    async def set(self, ctx: GrowTube, *, content: str):
        self.news = content
        await ctx.reply("Oki")

    @commands.command(aliases=["wlt"])
    async def wallet(self, ctx: GrowContext, user: discord.User = None):
        """
        Get a user wallet information, yes you can check anyone wallet information
        """
        user = user or ctx.author
        result = await self.bot.pool.fetchrow(
            "SELECT currency FROM users WHERE id = $1", user.id
        )
        if result is None:
            raise MessagedError("this user does not have an account")
        embed = discord.Embed(
            title=f"{user} Wallet",
            description=f"**{currency_name}**: {result[0]:,} {currency_emoji}",
            color=embed_color,
            timestamp=utcnow(),
        )
        embed.set_thumbnail(url=user.display_avatar)
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.me.display_avatar
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def register(self, ctx: GrowContext):
        """
        Register yourself into the country
        """
        await self.bot.pool.execute("INSERT INTO users VALUES ($1, 0)", ctx.author.id)
        await ctx.reply("Registered!")

    @commands.command(aliases=["clt"])
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def collect(self, ctx: GrowContext):
        """
        Collect random items, maximum 2 use every 30 seconds
        """
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
    async def inventory(self, ctx: GrowContext):
        """`exit
        Get your inventory contents, TP stands for Total Price
        """
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
            items.append(f"TP: {price:<10,} | Q: {record[1]:<6,} | {record[0].title()}")
        if summed:
            items.append(f"\nEstimated Total Values: {sum(summed):,}")
        records = "\n".join(items) or "Empty...."
        await ctx.reply("```\n" + records + "```")

    @commands.command()
    @commands.check(_trade_check)
    async def sell(
        self,
        ctx: GrowContext,
        quantity: Optional[_quantity_convert] = 1,
        *,
        item_name,
    ):
        """
        Sells any item excluding non buyable
        """
        quantity: Union[int, Literal["all"]] = quantity
        if quantity != "all" and quantity <= 0:
            raise MessagedError("Invalid value for quantity")
        record = await self.bot.pool.fetchrow(
            "SELECT inventory.item_id, inventory.quantity, items.value, items.name, items.supply, items.demand, items.stock FROM inventory INNER JOIN items ON items.id = inventory.item_id WHERE LOWER(items.name) = $1 AND user_id = $2",
            item_name.lower(),
            ctx.author.id,
        )
        if record is None:
            raise MessagedError("You don't have this item")
        value = record[2]
        if quantity == "all":
            quantity = record[1]
        remaining = record[1] - quantity
        if remaining < 0:
            raise MessagedError("Quantity to be sold is bigger than actual quantity")
        currency = _calculate_price(value, record[5], record[4], 0, record[6])
        if currency < 0:
            currency = 0
        currency *= quantity
        total, tax = compute_transaction(currency)
        currency = currency - (total - currency)
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
                    create_task(
                        self.bot.redis.publish(
                            "market",
                            json.dumps(
                                {
                                    "id": record[0],
                                    "name": record[3],
                                    "value": value,
                                    "demand": record[5],
                                    "supply": record[4] + 1,
                                    "stock": record[6] + quantity,
                                }
                            ),
                        )
                    )
                    await conn.execute(
                        "UPDATE users SET currency = currency + $1 WHERE id = $2",
                        currency,
                        ctx.author.id,
                    )
            await ctx.send(
                f"Sold **{quantity:,}** {record[3]} for **{currency:,} {currency_name}** {currency_emoji} with {tax}% tax"
            )

    @commands.command()
    @commands.check(_trade_check)
    async def buy(self, ctx: GrowContext, quantity: Optional[int] = 1, *, item_name):
        """
        Buys an item from the market excluding non buyable
        """
        if quantity <= 0:
            raise MessagedError("Quantity is less than 0")
        record = await self.bot.pool.fetchrow(
            "SELECT items.id, items.value, items.name, items.supply, items.demand, items.stock FROM items WHERE LOWER(items.name) = $1 AND buyable",
            item_name.lower(),
        )
        if record is None:
            raise MessagedError("Item not found")
        if record[5] == 0:
            raise MessagedError("Stock is empty....")
        currency = await self.bot.pool.fetchval(
            "SELECT currency FROM users WHERE id = $1", ctx.author.id
        )
        if record is None:
            raise MessagedError("You don't have this item")
        value = record[1]
        price = _calculate_price(value, record[4], record[3], 0, record[5])
        if price < 0:
            price = 1
        price_total, tax = compute_transaction(price * quantity)
        remaining = currency - price_total
        if remaining < 0:
            raise MessagedError(f"You dont have enough {currency_name}")
        elif (record[5] - quantity) < 0:
            raise MessagedError("Quantity is bigger than available stock")
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
                create_task(
                    self.bot.redis.publish(
                        "market",
                        json.dumps(
                            {
                                "id": record[0],
                                "name": record[2],
                                "value": value,
                                "demand": record[4] + 1,
                                "supply": record[3],
                                "stock": record[5] - quantity,
                            }
                        ),
                    )
                )
                await conn.execute(
                    "UPDATE users SET currency = $1 WHERE id = $2",
                    remaining,
                    ctx.author.id,
                )
            await ctx.send(
                f"Bought **{quantity:,}** {record[2]} for **{price_total:,} {currency_name}** {currency_emoji} with {tax}% tax"
            )

    @commands.command(aliases=["mkt", "ma"])
    async def market(self, ctx: GrowContext):
        """
        List items prices and quantities
        """
        records = await self.bot.pool.fetch(
            "SELECT id, name, value, demand, supply, stock FROM items WHERE buyable ORDER BY id ASC"
        )
        items = [
            f"P: {_calculate_price(record[2], record[3], record[4], 0, record[5]):<10,} Q: {record[5]: <5} {record[1]}"
            for record in records
        ]
        await ctx.send("```\n" + ("\n".join(items)) + "\n```")

    @commands.command()
    async def top(self, ctx: GrowContext, limit: Optional[int] = 10):
        """
        List top [limit] users with the highest amount of currency
        """

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
    async def transfer(self, ctx: GrowContext, user: discord.User, amount: int):
        """
        Transfers money from your wallet to another user wallet
        """
        if user == ctx.author.id:
            return await ctx.reply("Haha no")
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
