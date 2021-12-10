from typing import Any, Optional
from discord import ui
from discord.ext import commands
import discord


class ConfirmView(ui.View):
    def __init__(self, context: commands.Context, /, *, responded=None, delete_after=True, **kwargs: Any):
        super().__init__(**kwargs)
        self.ctx = context
        self._result = None
        self.message = None
        self.delete_after = delete_after
        self.responded = responded or context.author

    async def prompt(self, *args: str, **kwargs: Any) -> Optional[bool]:
        self.message = await self.ctx.send(*args, view=self, **kwargs)
        await self.wait()
        return self.result

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.responded.id != getattr(interaction.user, "id", None):
            await interaction.response.send_message(
                f"Only {self.responded} can respond to this message!",
                ephemeral=True
            )
            return False
        return True


    async def stopping(self):
        if self.delete_after:
            await self.message.delete(delay=0)
        else:
            for item in self.children:
                item.disabled = True

            await self.message.edit(view=self)

    def stop(self):
        super().stop()
        self.ctx.bot.loop.create_task(self.stopping())

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value):
        self._result = value
        self.stop()

    @ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, button: ui.Button, interaction: discord.Interaction):
        self.result = True

    @ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, button: ui.Button, interaction: discord.Interaction):
        self.result = False
