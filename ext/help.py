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

    async def send_bot_help(
        self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]
    ):
        valid_commands: Dict[Optional[commands.Cog], Set[commands.Command]] = {}
        for key, value in mapping.items():
            _commands = set()
            for cmd in value:
                can_run = await self._can_run(self.context, cmd)
                if can_run:
                    _commands.add(cmd)
            if _commands:
                valid_commands[key] = _commands
        embed = discord.Embed(
            title="List of commands and categories",
            color=embed_color,
            timestamp=discord.utils.utcnow(),
        )
        for cog, _commands in valid_commands.items():
            if cog is None:
                cog = "Not Categorized"
            else:
                cog = cog.qualified_name
            embed.add_field(
                name=f"**{cog}**",
                value="```\n{}\n```".format(", ".join(i.name for i in _commands)),
            )
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog):
        valid_commands = set()
        for cmd in cog.get_commands():
            if await self._can_run(self.context, cmd):
                valid_commands.add(cmd)
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
            name="commands", value=", ".join((i.qualified_name for i in valid_commands))
        )

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command: commands.Command):
        if not await self._can_run(self.context, command):
            return self.command_not_found(self.command)
        embed = discord.Embed(
            title=f"Help for {command.qualified_name}",
            description=command.help or "No description",
            color=embed_color,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Usage", value=f"```\n{self.get_command_signature(command)}\n```"
        )
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        if not await self._can_run(self.context, group):
            return self.command_not_found(self.command)
        embed = discord.Embed(
            title=f"Help for {group.qualified_name}",
            description=group.help or "No description",
            color=embed_color,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Usage", value=f"```\n{self.get_command_signature(group)}\n```"
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
        if isinstance(command, commands.Group):
            return f"'{self.command.rstrip(string).rstrip()}' doesn't have any subcommand named {string}"
        else:
            return f"'{self.command.rstrip(string).rstrip()}' doesn't seem to have any subcommands"


def setup(bot: GrowTube) -> None:
    bot.help_command = Help()
    bot.log.info(f"Loaded {__file__}")
