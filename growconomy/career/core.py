from discord.ext import commands
from bot import GrowContext, GrowTube, MessagedError
from growconomy.constants import currency_name
from growconomy.views import ConfirmView


class Career(commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot
    
    async def cog_check(self, ctx: GrowContext):
        data = await self.bot.pool.fetchval("SELECT 1 FROM users WHERE id = $1", ctx.author.id)
        if data is None:
            raise MessagedError("You're not registered")
        return True

    @commands.command()
    async def career(self, ctx: GrowContext, career_id: int):
        c_career, c_position, c_pay = (await self.bot.pool.fetchrow(
            "SELECT careers.name, positions.name, positions.pay FROM users JOIN positions ON positions.id = users.position JOIN careers ON careers.id = users.career WHERE users.id = $1",
            ctx.author.id,
        )) or [None, None, None]
        if c_career:
            view = ConfirmView(ctx, timeout=60, delete_after=None)
            res = await view.prompt(
                "Are you sure you want to repick your career?\n"
                f"You're currently working as a **{c_career}**, as a **{c_position}** with a pay of **{c_pay:,} {currency_name}**",
            )
            if not res:
                return await view.message.reply("aborting")
