from asyncpg import Connection
from discord import Embed, User
from discord.utils import utcnow
from discord.ext import commands
from bot import GrowContext, GrowTube, MessagedError
from growconomy.constants import currency_name, embed_color, currency_emoji
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

    @commands.group(invoke_without_command=True)
    async def career(self, ctx: GrowContext):
        await ctx.send_help(ctx.command)

    @career.command(name="list")
    async def _list(self, ctx: GrowContext):
        careers = await self.bot.pool.fetch(
            "SELECT careers.id, careers.name, COUNT(positions.id) AS positions FROM careers JOIN positions ON careers.id = positions.career GROUP BY careers.id"
        )
        embed = Embed(
            title="List of careers",
            description="\n".join(
                f"**{i[1]}** with **{i[2]}** positions, id: {i[0]}" for i in careers
            ),
            color=embed_color,
        )
        return await ctx.reply(embed=embed)

    @career.command()
    async def info(self, ctx: GrowContext, user: User = None):
        user = user or ctx.author
        c_name, pos_name, pos_pay = (
            await self.bot.pool.fetchrow(
                "SELECT careers.name, positions.name, positions.pay FROM users JOIN careers ON careers.id = users.career JOIN positions ON positions.id = users.position WHERE users.id = $1",
                ctx.author.id,
            )
        ) or [None, None, None]
        if c_name is None:
            raise MessagedError(
                f"{f'`{user.display_name}`' if user != ctx.author else 'You'} seems to be unemployed"
            )
        await ctx.send(
            embed=Embed(
                timestamp=utcnow(),
                color=embed_color,
            )
            .set_author(name=user.display_name, icon_url=user.display_avatar)
            .add_field(name="Job name", value=c_name)
            .add_field(name="Position", value=pos_name)
            .add_field(
                name=f"Wage", value=f"{pos_pay:,} {currency_name} {currency_emoji}"
            )
        )

    @career.command()
    async def change(self, ctx: GrowContext, career_id: int):
        async with self.bot.pool.acquire() as conn:
            oc_name, op_id, op_pay = (
                await conn.fetchrow(
                    "SELECT careers.name, positions.name, positions.pay FROM users JOIN positions ON positions.id = users.position JOIN careers ON careers.id = users.career WHERE users.id = $1",
                    ctx.author.id,
                )
            ) or [None, None, None]
            conn: Connection
            if career_id == 0:
                if oc_name is None:
                    return await ctx.reply("You're already unemployed dummy")
                view = ConfirmView(ctx, timeout=60, delete_after=None)
                await view.prompt("Are you sure you want to quit your job?")
                if not view.result:
                    return await view.message.reply("aborting")

                await self.bot.pool.execute(
                    "UPDATE users SET career = NULL, position = NULL WHERE id = $1",
                    ctx.author.id,
                )
                return await ctx.send(
                    "Congratulations, you're now unemployed. Have fun eating pizza 24/7"
                )
            pos_id, pos_name, c_name, pos_pay = (
                await conn.fetchrow(
                    "SELECT positions.id, positions.name, careers.name, positions.pay FROM positions JOIN careers ON careers.id = positions.career WHERE privilege = (SELECT MAX(privilege) FROM positions) AND careers.id = $1 ORDER BY RANDOM() LIMIT 1",
                    career_id,
                )
            ) or [None, None, None, None]
            if pos_id is None:
                raise MessagedError("Invalid career id")

            view = ConfirmView(ctx, timeout=60, delete_after=None)
            if oc_name:
                text = (
                    "Are you sure you want to repick your job?\n"
                    f"You're currently working as a **{oc_name}**, with **{op_id}** position and with a pay of **{op_pay:,} {currency_name}**\n"
                    f"Changing to **{c_name}**, with **{pos_name}** positions and a pay of **{pos_pay:,} {currency_name}** {currency_emoji}"
                )
            else:
                text = f"Are you sure you want to be a **{c_name}** as **{pos_name}** with a pay of **{pos_pay:,} {currency_name}** {currency_emoji} (You can change career anytime)"
            await view.prompt(text)
            if not view.result:
                return await view.message.reply("aborting")

            await self.bot.pool.execute(
                "UPDATE users SET career = $1, position = $2 WHERE id = $3",
                career_id,
                pos_id,
                ctx.author.id,
            )
            await ctx.send(f"Changed your career to **{c_name}** as a **{pos_name}**")
