from bot import GrowTube
from discord.ext import commands
from typing import Dict, List, Optional, NamedTuple, Literal, Union
from discord import User, Message, Embed
from secrets import token_urlsafe

confirm_emoji = "\U00002705"

class TradeItem(NamedTuple):
    type: Union[Literal[0], Literal[1]] # 0 for item, 1 for currency
    name: Optional[str]
    amount: int

class TradeSession(NamedTuple):
    users: List[int]
    items: Dict[int, List[TradeItem]]
    id: str

class Trading:
    bot: GrowTube

    def __init__(self):
        self.users: Dict[int, TradeSession] = {}
        self.trades: Dict[str, Tuple[Message, Embed, TradeSession]] = {}

    async def _update_message(self, ctx, session: TradeSession):
        msg, embed = self.trades[session.id][0:2]
        msg = ctx.channel.get_partial_message(msg)
        index = session.users.index(ctx.author.id)
        embed.set_field_at(index, value = ", ".join([f"{i.amount} Growcoin" if i.type == 1 else f"{i.amount} {i.name}" for i in session.items[ctx.author.id]]))
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
                msg = await ctx.send(f"{ctx.author.mention} wants to trade with you {user.mention}, please react with {confirm_emoji} to accept")
                await msg.add_reaction(confirm_emoji)
                def _check(r, u):
                    return str(r) == confirm_emoji and u.id == user.id
                try:
                    await self.bot.wait_for("reaction_add", check=_check, timeout=120)
                except Exception:
                    return await msg.reply("I waited too long")
                embed = Embed(
                    title=f"Trade session {session.id}",
                    colour=self.bot.EMBED_COLOUR
                )
                for user_id in session.users:
                    embed.add_field(name=str(self.bot.get_user(user_id)), value="No Items")
                msg = await msg.reply(embed=embed)
                self.users[user.id] = session
                self.trades[session.id] = (msg, embed, session)

        elif ctx.author.id not in self.users:
            raise commands.CommandError("You're not trading with anyone right now")

    @trade.command()
    async def cancel(self, ctx):
        session = self.users.pop(ctx.author.id)
        session.users.remove(ctx.author.id)
        self.trades.pop(session.id)
        self.users.pop(session.users[0])
        await ctx.reply("Cancelled trade")
