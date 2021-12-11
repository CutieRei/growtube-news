from asyncio.tasks import create_task, sleep
from asyncpg.connection import Connection
from bot import GrowTube
from discord.ext import commands
from typing import Dict, List, Optional, Literal, Tuple
from discord import User, Message, Embed
from secrets import token_urlsafe
from discord.utils import find
from asyncio import Event
from .views import ConfirmView
from .constants import *
from .utils import async_any, GrowContext
import dataclasses


@dataclasses.dataclass(repr=True, eq=True)
class TradeItem:
    type: Literal[0, 1] = dataclasses.field(compare=False)  # 0 for item, 1 for currency
    amount: int = dataclasses.field(compare=False)
    name: Optional[str] = dataclasses.field(default=None)


@dataclasses.dataclass(repr=True, eq=True)
class TradeSession:
    users: List[int]
    items: Dict[int, Dict[str, TradeItem]]
    id: str
    is_accepting: bool = False
    user_accepting: Optional[int] = None
    accepted: Event = dataclasses.field(default_factory=Event)
    cancelled: Event = dataclasses.field(default_factory=Event)

def _check(ctx: GrowContext):
    cog: Trading = ctx.cog
    session = cog.users.get(ctx.author.id)
    if session is not None:
        if session.id in cog.trades:
            return True
    raise commands.CommandError("You're not trading with anyone")

class Trading:
    bot: GrowTube

    def __init__(self) -> None:
        self.users: Dict[int, TradeSession] = {}
        self.trades: Dict[str, Tuple[Message, Embed, TradeSession]] = {}

    async def _update_message(self, ctx: GrowContext, session: TradeSession):
        msg, embed = self.trades[session.id][0:2]
        index = session.users.index(ctx.author.id)
        embed.set_field_at(
            index,
            name=str(ctx.author),
            value=", ".join(
                [
                    f"{i.amount:,} {currency_name}"
                    if i.type == 1
                    else f"{i.amount:,} {i.name}"
                    for i in session.items[ctx.author.id].values()
                ]
            ) or "No Items",
        )
        await msg.edit(embed=embed)

    @commands.group(invoke_without_command=True)
    async def trade(self, ctx: GrowContext, user: User = None):
        if not ctx.invoked_subcommand:
            if not user:
                return
            elif ctx.author == user:
                await ctx.reply("You can't trade with yourself dummy")
            elif ctx.author.id in self.users:
                await ctx.reply("You're already trading with someone")
            elif user.id in self.users:
                await ctx.reply(f"**{user}** is already trading")
            elif not await self.bot.pool.fetchval(
                "SELECT 1 FROM users WHERE id = $1", user.id
            ):
                await ctx.reply("User is not registered")
            else:
                session = TradeSession(
                    users=[ctx.author.id, user.id],
                    items={ctx.author.id: {}, user.id: {}},
                    id=token_urlsafe(6),
                )
                self.users[ctx.author.id] = session
                view = ConfirmView(ctx, responded=user, delete_after=False, timeout=30)
                res = await view.prompt(
                    f"{ctx.author.mention} wants to trade with you {user.mention}"
                )
                if not res:
                    self.users.pop(ctx.author.id)
                    await view.message.reply(f"{user} denied the trade request")
                    return
                embed = Embed(title=f"Trade session {session.id}", colour=embed_color)
                for user_id in session.users:
                    embed.add_field(
                        name=str(self.bot.get_user(user_id)), value="No Items"
                    )
                msg = await view.message.reply(embed=embed)
                self.users[user.id] = session
                self.trades[session.id] = (msg, embed, session)

        elif ctx.author.id not in self.users and self.trades.get(self.users[ctx.author.id]) is None:
            raise commands.CommandError("You're not trading with anyone right now")
        elif self.trades.get(self.users[ctx.author.id]) is None:
            raise commands.CommandError("You're not trading with anyone right now")

    @trade.command()
    @commands.check(_check)
    async def cancel(self, ctx: GrowContext):
        session = self.users.pop(ctx.author.id)
        if session.cancelled.is_set():
            await sleep(0)
            session.cancelled.set()
        session.users.remove(ctx.author.id)
        data = self.trades.pop(session.id)
        msg, embed, _ = data
        self.users.pop(session.users[0])
        embed.description = "Trade Cancelled"
        await msg.edit(embed=embed)
        await msg.reply("Cancelled trade")
    
    @trade.command()
    @commands.check(_check)
    async def accept(self, ctx: GrowContext):
        session = self.users[ctx.author.id]
        if session.is_accepting and session.user_accepting == ctx.author.id:
            return
        view = ConfirmView(ctx, delete_after=False, timeout=30)
        res = await view.prompt(
            f"{ctx.author.mention} are you sure you want accept?"
        )
        if res:
            if session.is_accepting:
                return session.accepted.set()
            session.is_accepting = True
            session.user_accepting = ctx.author.id
            user2: int = find(lambda user: user != ctx.author.id, session.users)
            create_task(view.message.edit(f"Waiting for {self.bot.get_user(user2)}"))
            await async_any(
                session.accepted.wait(),
                session.cancelled.wait(),
            )
            if session.cancelled.is_set():
                session.is_accepting = False
                session.user_accepting = None
                session.accepted.clear()
                create_task(view.message.edit(f"{self.bot.get_user(user2)} cancelled confirmation"))
                return await ctx.reply(
                    f"{self.bot.get_user(user2)} cancelled the trade confirmation"
                )
            else:
                create_task(view.message.edit(f"{self.bot.get_user(user2)} accepted!"))
                async with self.bot.pool.acquire() as conn:
                    conn: Connection
                    u1_inv = await conn.fetch(
                        """
                        SELECT items.name, inventory.item_id, inventory.quantity FROM inventory 
                        INNER JOIN items ON items.id = inventory.item_id WHERE user_id = $1
                        """,
                        ctx.author.id,
                    )
                    u2_inv = await conn.fetch(
                        """
                        SELECT items.name, inventory.item_id, inventory.quantity FROM inventory 
                        INNER JOIN items ON items.id = inventory.item_id WHERE user_id = $1
                        """,
                        user2,
                    )

                    async with conn.transaction():
                        items = session.items
                        incr_updates = []
                        decr_updates = []
                        update_currency = []
                        inserts = []
                        deletes = []
                        inv = {
                            ctx.author.id: {i[0].lower(): i for i in u1_inv},
                            user2: {i[0].lower(): i for i in u2_inv},
                        }
                        if None in items[ctx.author.id] or None in items[user2]:
                            c1 = items[ctx.author.id].pop(None, None)
                            c2 = items[user2].pop(None, None)
                            currencies = await conn.fetch(
                                "SELECT id, currency FROM users WHERE id in ($1, $2)",
                                ctx.author.id,
                                user2,
                            )

                            if c1 and c2:
                                cr1 = find(lambda x: x[0] == ctx.author.id, currencies)
                                cr2 = find(lambda x: x[0] == user2, currencies)
                                t1 = cr1[1] - c1.amount + c2.amount
                                t2 = cr2[1] - c2.amount + c1.amount
                                update_currency.append([t1, ctx.author.id])
                                update_currency.append([t2, user2])
                            else:
                                if c1:
                                    cr1 = find(
                                        lambda x: x[0] == ctx.author.id, currencies
                                    )
                                    update_currency.append(
                                        [cr1[1] - c1.amount, ctx.author.id]
                                    )
                                    update_currency.append([cr1[1] + c1.amount, user2])
                                if c2:
                                    cr2 = find(lambda x: x[0] == user2, currencies)
                                    update_currency.append([cr2[1] - c2.amount, user2])
                                    update_currency.append(
                                        [cr2[1] + c2.amount, ctx.author.id]
                                    )
                        def compute(user_id: int, user_id2: int):
                            for item in inv[user_id].values():
                                amount: int = item[2]
                                item_id: int = item[1]
                                item = items[user_id].get(item[0].lower())
                                if item is not None:
                                    amount_left = amount - item.amount
                                    if amount_left > 0:
                                        decr_updates.append([item.amount, item_id, user_id])
                                    else:
                                        deletes.append([item_id, user_id])

                                    item_2 = inv[user_id2].get(item.name.lower())
                                    if item_2 is not None:
                                        incr_updates.append(
                                            [item.amount, item_id, user_id2]
                                        )
                                    else:
                                        inserts.append([item_id, user_id2, item.amount])

                        for i in (
                            [ctx.author.id, user2],
                            [user2, ctx.author.id],
                        ):
                            compute(i[0], i[1])

                        if incr_updates:
                            await conn.executemany(
                                "UPDATE inventory SET quantity = quantity + $1 WHERE item_id = $2 and user_id = $3",
                                incr_updates,
                            )
                        if decr_updates:
                                await conn.executemany(
                                "UPDATE inventory SET quantity  = quantity - $1 WHERE item_id = $2 and user_id = $3",
                                decr_updates,
                            )
                        if update_currency:
                            await conn.executemany(
                                "UPDATE users SET currency = $1 WHERE id = $2",
                                update_currency,
                            )
                        if inserts:
                            await conn.executemany(
                                    "INSERT INTO inventory (item_id, user_id, quantity) VALUES ($1, $2, $3)",
                                    inserts,
                            )
                        if deletes:
                            await conn.executemany(
                                "DELETE FROM inventory WHERE item_id = $1 AND user_id = $2",
                                deletes,
                            )
                        await ctx.send(
                            f"{ctx.author} sucessfully traded with {self.bot.get_user(user2)}"
                        )
                        self.trades.pop(session.id)
                        self.users.pop(ctx.author.id)
                        self.users.pop(user2)
                        return
        else:
            session.is_accepting = False
            session.accepted.clear()
            session.cancelled.set()
            await sleep(0)
            session.cancelled.unset()
            await ctx.reply("Cancelled")

    @trade.command()
    @commands.check(_check)
    async def add(self, ctx: GrowContext, amount: Optional[int] = 1, *, item_name: str = None):
        if amount < 0:
            return
        session = self.users[ctx.author.id]
        if session.is_accepting:
            return
        if item_name is None:
            currency = await self.bot.pool.fetchval(
                "SELECT currency FROM users WHERE id = $1", ctx.author.id
            )
            if currency < amount:
                return await ctx.reply("You don't have enough {currency_name}")
            items = self.users[ctx.author.id].items[ctx.author.id]
            try:
                item = items[None]
                if item.amount + amount > currency:
                    return await ctx.reply(f"You don't have enough {currency_name}")
                item.amount += amount
            except KeyError:
                items[None] = TradeItem(type=1, amount=amount)

            await self._update_message(ctx, self.users[ctx.author.id])
            return await ctx.reply(f"Added **{amount}** {currency_name}")
        else:
            item_name = item_name.lower()
            item = await self.bot.pool.fetchrow(
                """
                SELECT items.name, inventory.item_id, inventory.quantity FROM inventory
                INNER JOIN items ON items.id = inventory.item_id
                WHERE LOWER(items.name) = $1 and inventory.user_id = $2
                """,
                item_name,
                ctx.author.id,
            )
            if item is None:
                return await ctx.reply("You don't have this item")
            if (item[2] - amount) < 0:
                return await ctx.reply(f"You don't have enough {item[0]}")
            name = item[0]
            real_amount = item[2]
            try:
                item = session.items[ctx.author.id][name]
                if (item.amount + amount) > real_amount:
                    return await ctx.reply(f"You don't have enough {item[0]}")
                item.amount += amount
            except Exception:
                session.items[ctx.author.id][item_name] = TradeItem(type=0, amount=amount, name=name)
            
            await self._update_message(ctx, self.users[ctx.author.id])
            return await ctx.reply(f"Added **{amount}** {name}")

    @trade.command()
    @commands.check(_check)
    async def remove(self, ctx: GrowContext, amount: Optional[int] = 1, *, item_name: str = None):
        if amount < 0:
            return
        session = self.users[ctx.author.id]
        if session.is_accepting:
            return
        if item_name is None:
            items = self.users[ctx.author.id].items[ctx.author.id]
            try:
                item = items[None]
                if item.amount - amount < 0:
                    return await ctx.reply(f"You don't have {amount} {currency_name} in trade")
                item.amount -= amount
                if item.amount == 0:
                    session.items[ctx.author.id].pop(None)
            except KeyError:
                return await ctx.reply(f"You don't have {amount} {currency_name} in trade")

            await self._update_message(ctx, self.users[ctx.author.id])
            return await ctx.reply(f"Removed **{amount}** {currency_name}")
        else:
            item_name = item_name.lower()
            try:
                item = session.items[ctx.author.id][item_name]
                if (item.amount - amount) < 0 :
                    return await ctx.reply(f"You don't have {amount} '{item.name}'")
                item.amount -= amount
                if item.amount == 0:
                    session.items[ctx.author.id].pop(item_name)
            except Exception:
                return await ctx.reply(f"You don't have '{item_name}' in trade")
            await self._update_message(ctx, self.users[ctx.author.id])
            return await ctx.reply(f"Removed **{amount}** '{item.name}'")
