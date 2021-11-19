from typing import Coroutine, List, Mapping, Optional, Union
from discord.ext import commands
import discord
import datetime

embed_color = discord.Color(15007744)

class Help(commands.HelpCommand):

    command: str

    async def prepare_help_command(self, ctx, command):
        self.command = command

    async def _can_run(self, ctx: commands.Context, command: commands.Command) -> Coroutine[bool, None, None]:
        try:
            return await command.can_run(ctx)
        except Exception:
            return False
    
    async def command_not_found(self, string: str) -> str:
        return f"Cannot find any command or category named '{string}'"
    
    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]):
        valid_commands = {}
        for key, value in mapping.items():
            _commands = set()
            for cmd in value:
                can_run = await self._can_run(self.context, cmd)
                if can_run:
                    _commands.add(cmd)
            if _commands:
                valid_commands[key] = _commands
        embed = discord.Embed(
            title = "List of commands and categories",
            description = "\n".join("**{}**\n{}".format("Uncategorized" if key is None else key.qualified_name, ("\n".join(i.name for i in value))+"\n") for key, value in valid_commands.items()),
            color = embed_color,
            timestamp=datetime.datetime.utcnow()
        )
        await self.get_destination().send(embed=embed)
    
    async def send_cog_help(self, cog: commands.Cog):
        valid_commands = set()
        for cmd in cog.get_commands():
            if await self._can_run(self.context, cmd):
                valid_commands.add(cmd)
        if not valid_commands:
            return await self.command_not_found(self.command)

        embed = discord.Embed(
            title = f"Help for {cog.qualified_name}",
            description = cog.description or "No description",
            color = embed_color,
            timestamp = datetime.datetime.utcnow()
        )
        embed.add_field(name="commands", value=", ".join((i.qualified_name for i in valid_commands)))

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command: commands.Command):
        if not await self._can_run(self.context, command):
            return await self.command_not_found(self.command)
        embed = discord.Embed(
            title = f"Help for {command.qualified_name}",
            description = command.help or "No description",
            color = embed_color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Usage", value=f"```\n{self.get_command_signature(command)}\n```")
        await self.get_destination().send(embed=embed)
    
    async def send_group_help(self, group: commands.Group):
        if not await self._can_run(self.context, group):
            return await self.command_not_found(self.command)
        embed = discord.Embed(
            title = f"Help for {group.qualified_name}",
            description = group.help or "No description",
            color = embed_color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Usage", value=f"```\n{self.get_command_signature(group)}\n```")
        embed.add_field(name="Subcommands", value="```\n"+(", ".join(sub.name for sub in group.commands) or "none")+"\n```")
        await self.get_destination().send(embed=embed)
    
    async def subcommand_not_found(self, command: Union[commands.Group, commands.Command], string: str) -> str:
        if isinstance(command, commands.Group):
            return f"'{command.qualified_name}' doesn't have any subcommand named {string}"
        else:
            return f"'{command.qualified_name}' doesn't seem to have any subcommands"

def setup(bot: commands.Bot) -> None:
    bot.help_command = Help()
    print("Loaded help command")
