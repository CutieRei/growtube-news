from typing import Coroutine, Dict, List, Mapping, Optional, Set, Union
from discord.ext import commands
from bot import GrowTube
import discord


embed_color = GrowTube.EMBED_COLOUR


class Help(commands.HelpCommand):

    command: str

    async def prepare_help_command(self, ctx, command):
        self.command = command

    async def _can_run(
        self, ctx: commands.Context, command: commands.Command
    ) -> Coroutine[bool, None, None]:
        try:
            return await command.can_run(ctx)
        except Exception:
            return False

    def command_not_found(self, string: str) -> str:
        string = string.split()[0]
        return f"Cannot find any command or category named '{string}'"

    def get_command_signature(self, command: commands.Command):
        return super().get_command_signature(command).replace("_", " ")

    async def send_bot_help(
        self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]
    ):
        embed = discord.Embed(
            title="List of commands and categories",
            color=embed_color,
            timestamp=discord.utils.utcnow(),
        )
        for cog, _commands in mapping.items():
            if await self.filter_commands(_commands):
                cog = "Uncategorized" if cog is None else cog.qualified_name
                embed.add_field(
                    name=f"**{cog}**",
                    value="```\n{}\n```".format(", ".join(i.name for i in _commands)),
                )
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog):
        valid_commands = await self.filter_commands(cog.get_commands())
        if not valid_commands:
            return await self.get_destination().send(
                self.command_not_found(self.command)
            )

        embed = discord.Embed(
            title=f"Help for {cog.qualified_name}",
            description=cog.description or "No description",
            color=embed_color,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="commands",
            value=f"```{', '.join((i.qualified_name for i in valid_commands))}```",
        )

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command: commands.Command):
        embed = discord.Embed(
            title=f"Help for {command.qualified_name}",
            description=command.help or "No description",
            color=embed_color,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Usage",
            value=f"```\n{self.get_command_signature(command)}\n```",
        )
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        embed = discord.Embed(
            title=f"Help for {group.qualified_name}",
            description=group.help or "No description",
            color=embed_color,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Usage",
            value=f"```\n{self.get_command_signature(group)}\n```",
        )
        embed.add_field(
            name="Subcommands",
            value="```\n"
            + (", ".join(sub.name for sub in group.commands) or "none")
            + "\n```",
        )
        await self.get_destination().send(embed=embed)

    def subcommand_not_found(
        self, command: Union[commands.Group, commands.Command], string: str
    ) -> str:
        return f"'{self.command.rstrip(string).rstrip()}' doesn't have any subcommand named {string}"


def setup(bot: GrowTube) -> None:
    bot.help_command = Help(verify_checks=True, aliases=["halp"])
    bot.log.info(f"Loaded {__file__}")
