from asyncpg import Connection
from discord import Embed
from discord.ext import commands
from bot import GrowContext, GrowTube, MessagedError
from growconomy.constants import currency_name, embed_color
from growconomy.views import ConfirmView


class Career(commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot

    async def cog_check(self, ctx: GrowContext):
        data = await self.bot.pool.fetchval(
            "SELECT 1 FROM users WHERE id = $1", ctx.author.id
        )
        if data is None:
            raise MessagedError("You're not registered")
        return True

    @commands.command()
    async def career(self, ctx: GrowContext, career_id: int = None):
        if career_id is None:
            careers = await self.bot.pool.fetch(
                "SELECT careers.id, careers.name, COUNT(positions.id) AS positions FROM careers JOIN positions ON careers.id = positions.career GROUP BY careers.id"
            )
            embed = Embed(
                title="List of careers",
                description="\n".join(
                    f"**{i[0]}** with **{i[1]}** positions, id: {i[2]}" for i in careers
                ),
                color=embed_color,
            )
            return await ctx.reply(embed=embed)

        async with self.bot.pool.acquire() as conn:
            conn: Connection
            pos_id, pos_name, c_name, = (
                await conn.fetchrow(
                    "SELECT positions.id, positions.name, careers.name FROM positions JOIN careers ON careers.id = positions.career WHERE privilege = (SELECT MAX(privilege) FROM positions) AND careers.id = $1 ORDER BY RANDOM() LIMIT 1",
                    career_id,
                )
            ) or [None, None, None]
            if pos_id is None:
                raise MessagedError("Invalid career id")

            oc_name, op_id, op_pay = (
                await conn.fetchrow(
                    "SELECT careers.name, positions.name, positions.pay FROM users JOIN positions ON positions.id = users.position JOIN careers ON careers.id = users.career WHERE users.id = $1",
                    ctx.author.id,
                )
            ) or [None, None, None]
            view = ConfirmView(ctx, timeout=60, delete_after=None)
            if oc_name:
                text = (
                    "Are you sure you want to repick your career?\n"
                    f"You're currently working as a **{oc_name}**, as a **{op_id}** with a pay of **{op_pay:,} {currency_name}**"
                )
            else:
                text = "Are you sure? (You can change career anytime)"
            res = await view.prompt(text)
            if not res:
                return await view.message.reply("aborting")

            await self.bot.pool.execute(
                "UPDATE users SET career = $1, position = $2", career_id, pos_id
            )
            await ctx.send(f"Changed your career to **{c_name}** as a **{pos_name}**")
