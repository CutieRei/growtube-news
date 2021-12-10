from bot import GrowTube
from discord.ext import commands
from typing import Dict, List, Optional, Literal, Union
from discord import User, Message, Embed
from secrets import token_urlsafe
from discord.utils import find
from asyncio import Event
from .views import ConfirmView
from .constants import *
from .utils import async_any
import dataclasses

@dataclasses.dataclass(repr=True, eq=True)
class TradeItem:
    type: Union[Literal[0], Literal[1]] = dataclasses.field(compare=False) # 0 for item, 1 for currency
    amount: int = dataclasses.field(compare=False)
    name: Optional[str] = dataclasses.field(default=None)

@dataclasses.dataclass(repr=True, eq=True)
class TradeSession:
    users: List[int]
    items: Dict[int, List[TradeItem]]
    id: str
    is_accepting: bool = False
    cancelled: Event = dataclasses.field(default_factory=Event)

class Trading:
    bot: GrowTube

    def __init__(self):
        self.users: Dict[int, TradeSession] = {}
        self.trades: Dict[str, Tuple[Message, Embed, TradeSession]] = {}

    async def _update_message(self, ctx, session: TradeSession):
        msg, embed = self.trades[session.id][0:2]
        index = session.users.index(ctx.author.id)
        embed.set_field_at(index, name=str(ctx.author), value = ", ".join([f"{i.amount:,} {currency_name}" if i.type == 1 else f"{i.amount:,} {i.name}" for i in session.items[ctx.author.id]]))
        await msg.edit(embed=embed)

    @commands.group(invoke_without_command=True)
    async def trade(self, ctx, user: User = None):
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
                session = TradeSession(users=[ctx.author.id, user.id], items={ctx.author.id: [], user.id: []}, id=token_urlsafe(6))
                self.users[ctx.author.id] = session
                view = ConfirmView(ctx, responded=user, delete_after=None)
                res = await view.prompt(f"{ctx.author.mention} wants to trade with you {user.mention}")
                if not res:
                    self.users.pop(ctx.author.id)
                    await view.message.reply(f"{user} denied the trade request")
                    return
                embed = Embed(
                    title=f"Trade session {session.id}",
                    colour=embed_color
                )
                for user_id in session.users:
                    embed.add_field(name=str(self.bot.get_user(user_id)), value="No Items")
                msg = await view.message.reply(embed=embed)
                self.users[user.id] = session
                self.trades[session.id] = (msg, embed, session)

        elif ctx.author.id not in self.users:
            raise commands.CommandError("You're not trading with anyone right now")
        elif self.trades.get(self.users[ctx.author.id]) is None:
            raise commands.CommandError("You're not tra    ding with anyone right now")

    @trade.command()
    async def cancel(self, ctx):
        session = self.users.pop(ctx.author.id)
        session.users.remove(ctx.author.id)
        msg, embed, _ = self.trades.pop(session.id)
        self.users.pop(session.users[0])
        embed.description="Trade Cancelled"
        await msg.edit(embed=embed)
        await msg.reply("Cancelled trade")

    @trade.command()
    async def accept(self, ctx):
        res = await ConfirmView(ctx).prompt(f"{ctx.author.mention} are you sure you want accept?")
        if res:
            session = self.users[ctx.author.id]
            session.is_accepting = True
            user2 = find(lambda user: user != ctx.author.id, session.users)
            task = ...
        await ctx.reply("Cancelled")
        
        

    @trade.command()
    async def add(self, ctx, amount: Optional[int] = 1, *,  item_name):
        item_name = item_name.lower()
        if item_name == "currency":
            currency = await self.bot.pool.fetchval("SELECT currency FROM users WHERE id = $1", ctx.author.id)
            if currency < amount:
                return await ctx.reply("You don't have enough {currency_name}")
            items = self.users[ctx.author.id].items[ctx.author.id]
            item = TradeItem(type=1, amount=amount)
            try:
                item = items[items.index(item)]
                if item.amount + amount > currency:
                    return await ctx.reply(f"You don't have enough {currency_name}")
            except Exception:
                items.append(item)
            
            await self._update_message(ctx, self.users[ctx.author.id])
            return await ctx.reply(f"Added **{amount}** {currency_name}")

