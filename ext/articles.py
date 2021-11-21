import aiohttp
import discord
import datetime
import asyncio
import storage
from typing import Dict, Optional, Tuple, Callable
from discord.ext.commands.errors import NoPrivateMessage
from discord import Embed, Color, TextChannel, utils, Webhook
from bot import GrowTube, NotPermittedForPublish
from discord.ext import commands

def from_hex(string):
    string = string.replace("#", "0x")
    return Color(int(string, 16))
emoji_url = "https://cdn.discordapp.com/emojis/803865449694494742.png"
embed_color = discord.Color(15007744)

class Channel:
    category1 = 0
    category2 = 1
    category3 = 2

_channel_dict = {
    Channel.category1: "Announcement",
    Channel.category2: "Contest",
    Channel.category3: "Growtopia Community"
}

embed_color = Color(15007744)

admin_id = 877549553153376306
news_types: Dict[str, Tuple[str, Color, int]] = {
    "growtopia news": ("Growtopia News", from_hex("#239e1b"), Channel.category1),
    "growtopia announcement": ("Growtopia Announcement", from_hex("#67e85f"), Channel.category1),
    "growtube announcement": ("Growtube Announcement", from_hex("#ffffff"), Channel.category1),
    "wotd": ("World Of The Day", from_hex("#f7e91b"), Channel.category2),
    "votw": ("Video Of The Week", from_hex("#ffffff"), Channel.category2),
    "forums": ("Community Forums", from_hex("#10eb90"), Channel.category3),
    "guidebook": ("Community Guidebook", from_hex("#eb8810"), Channel.category3),
    "suggestions": ("Community Suggestions", from_hex("#0a22f7"), Channel.category3)
}

server_status: Dict[str, Tuple[str, str, Color]] = {
    "Online": ("Server is online", "<:gtonline:874224931188146216>", Color.green()),
    "Maintenance": ("Server is on maintenance", "<:gtbusy:874224931230060604>", Color.red()),
    "Extended Maintenance": ("The maintenance is extended", "<:gtaway:874224931389472778>", Color.gold())
}

color = discord.ButtonStyle.gray

class QuitError(Exception):
    
    def __init__(self, msg=None, message=None):
        self.msg = msg or ""
        self.message = message

    def __str__(self):
        return self.msg

async def message_wait(ctx: commands.Context, predicate: Callable[[discord.Message], bool], input, msg="Invalid value!") -> discord.Message:
    bot: GrowTube = ctx.bot
    await ctx.send(input+". Enter `cancel` to exit.")
    while True:
        message = await bot.wait_for("message", check=lambda x: x.author == ctx.author and x.channel == ctx.channel)
        if message.content.lower() == "cancel":
            raise QuitError(message=message)
        elif predicate is None or predicate(message):
            return message
        elif not predicate(message):
            await ctx.send(msg)

async def broadcast(chtype: int, ctx: commands.Context, *args, **kwargs):
    bot: GrowTube = ctx.bot
    channels = await bot.db.get_channels(chtype)

    async with aiohttp.ClientSession() as session:
        async def _send(channel):
            try:
                webhook = Webhook.partial(channel.webhook, channel.token, session=session)
                await webhook.send(*args, **kwargs, username=bot.user.name, avatar_url=bot.user.avatar.url)
            except Exception as e:
                print(repr(e))

        tasks = [asyncio.create_task(_send(i)) for i in channels]
        if not tasks:
            return
        return await asyncio.wait(tasks)
    
def get_time():
    return datetime.datetime.utcnow() - datetime.timedelta(hours=4)

async def _setchannel(ctx: commands.Context, chtype: int, channel_id: int, webhook_id: int) -> bool:

    bot: GrowTube = ctx.bot
    guild = ctx.guild
    channel = ctx.guild.get_channel(channel_id)
    if webhook_id is None:
        webhook: Webhook = await channel.create_webhook(name="GrowTube News")
    else:
        webhook: Webhook = utils.get(await channel.webhooks(), id=webhook_id)
        if not webhook:
            await ctx.send("Webhook not found")
            return False
    
    channels = await bot.db.get_guild(guild.id)
    channel = storage.Channel(guild.id, chtype, channel_id, webhook.id, webhook.token)
    if channels[chtype] is None:
        await bot.db.add_channel(channel)
    else:
        await bot.db.update_channel(channel)
    
    channel = guild.get_channel(channel.channel)
    await ctx.send(f"Successfully set **{_channel_dict[chtype]}** channel to {channel.mention}")
    return True

async def _deletechannel(ctx: commands.Context, chtype: int) -> bool:
    bot: GrowTube = ctx.bot
    channel = (await bot.db.get_guild(ctx.guild.id))[chtype]
    if channel is None:
        await ctx.send("Not attached to any channels")
        return False
    await bot.db.remove_channel(channel)
    await ctx.send(f"Removed channel for **{_channel_dict[chtype]}**")
    return True

def check(ctx: commands.Context):
    if not ctx.guild:
        raise NoPrivateMessage()
    elif ctx.author.get_role(admin_id):
        return True
    raise NotPermittedForPublish("You are not permitted to access the news configuration!")

def check_channel(ctx: commands.Context):
    try:
        return check(ctx)
    except NotPermittedForPublish:
        if ctx.channel.permissions_for(ctx.author).manage_channels:
            return True
    return False

class ServerView(discord.ui.View):

    def __init__(self, ctx: commands.Context, *, timeout: Optional[float] = None) -> None:
        super().__init__(timeout=timeout)
        self.type = None
        self.ctx = ctx

    def view_check(self, i: discord.Interaction):
        return self.ctx.author == i.user
    
    @discord.ui.button(label="Online", style=color)
    async def online(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if self.view_check(interaction):
            self.type = ("Online", server_status["Online"])
            self.stop()
    
    @discord.ui.button(label="Maintenance", style=color)
    async def maintenance(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if self.view_check(interaction):
            self.type = ("Maintenance", server_status["Maintenance"])
            self.stop()
    
    @discord.ui.button(label="Extended Maintenance", style=color)
    async def extended_maintenance(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if self.view_check(interaction):
            self.type = ("Extended Maintenance", server_status["Extended Maintenance"])
            self.stop()


class Articles(commands.Cog):

    bot: GrowTube

    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot
    
    @commands.command()
    @commands.check(check)
    async def maintenance(self, ctx):
        
        sview = ServerView(ctx, timeout=60)
        embed = Embed(
            color = embed_color,
            description = "What's the status of the server?"
        )
        await ctx.send(embed=embed, view=sview)
        await sview.wait()
        stype = sview.type
        if stype is None:
            return await ctx.send("I waited for too long!")
        try:
            msg = await message_wait(ctx, None, "Insert a description")
        except QuitError as e:
            return await e.message.add_reaction("✅")
        stype = stype[1]
        embed = Embed(
            color = stype[2],
            description = msg.content,
            timestamp = datetime.datetime.utcnow()
        )
        embed.set_author(name=stype[0], icon_url="https://cdn.discordapp.com/emojis/{}".format(stype[1].split(":")[-1].replace(">", "")))
        embed.set_footer(text=f"Growtube News | Published by {ctx.author}", icon_url=emoji_url)
        await broadcast(Channel.category1, ctx, embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.check(check_channel)
    async def channels(self, ctx: commands.Context):
        """
        If this command is called without any subcommands, it show's all the channel this server is attached to.
        """
        channels = await self.bot.db.get_guild(ctx.guild.id)
        to_render = []
        for channel in channels:
            chtype = channel.type
            if channel:
                channel = ctx.guild.get_channel(channel.channel)
                if channel is None:
                    channel = "[channel deleted]"
                else:
                    channel = channel.mention
            else:
                channel = "none"
            to_render.append(f"**{_channel_dict[chtype]}**: {channel}")

        embed = Embed(
            title = "Attached channels",
            description = "\n".join(to_render),
            color = embed_color,
            timestamp =  datetime.datetime.utcnow()
        )
        await ctx.send(embed=embed)
    
    @channels.group(invoke_without_command=True)
    async def set(self, ctx: commands.Context):
        "Set a channel news for this server, does nothing if called without subcommand"
        return
        
    @set.command(name="announcement")
    async def set_announcement(self, ctx: commands.Context, channel: TextChannel, webhook: Optional[int] = None):
        """
        Set `Growtopia Announcement, Growtopia News, Growtube News` news to be sent to this channel.
        """
        await _setchannel(ctx, Channel.category1, channel.id, webhook)

    @set.command(name="contest")
    async def set_contest(self, ctx: commands.Context, channel: TextChannel, webhook: Optional[int] = None):
        """
        Set `VOTW, WOTD` news to be sent to this channel.
        """
        await _setchannel(ctx, Channel.category2, channel.id, webhook)

    @set.command(name="growtopia-community", aliases=["community", "gt-community"])
    async def set_growtopia_community(self, ctx: commands.Context, channel: TextChannel, webhook: Optional[int] = None):
        """
        Set Growtopia Community `Forums, Guidebook, Suggestions` news to be sent to this channel.

        The alias 'community' is deprecated please migrate any automation to 'growtopia-community' or 'gt-community'
        """
        await _setchannel(ctx, Channel.category3, channel.id, webhook)

    @channels.group(invoke_without_command=True, aliases=["remove", "del", "rm"])
    async def delete(self, ctx: commands.Context):
        return

    @delete.command(name="announcement")
    async def del_announcement(self, ctx: commands.Context):
        await _deletechannel(ctx, Channel.category1)
    
    @delete.command(name="contest")
    async def del_contest(self, ctx: commands.Context):
        await _deletechannel(ctx, Channel.category2)
    
    @delete.command(name="growtopia-community", aliases=["community", "gt-community"])
    async def del_growtopia_community(self, ctx: commands.Context):
        await _deletechannel(ctx, Channel.category3)

    @commands.command()
    @commands.check(check)
    async def publish(self, ctx):
        """
        Publishes a news to everyone, news types affects which channel the news is sent to
        check out `setchannel` for more info.
        """
        try:
            title = await message_wait(ctx, None, "What's the title of this news?")
            ntype = await message_wait(ctx, lambda x: news_types.get(x.content.lower()), "What is the news type? (`{}`)".format(", ".join((i.title() if len(i) > 4 else i.upper() for i in news_types))), "Invalid type!")
            ntype, color, chtype = news_types[ntype.content.lower()]
            body = await message_wait(ctx, None, "And what would be the body of the news?")
            image = await message_wait(ctx, None, "Please insert an image link (or N/A if there's none)")
            image = image.content if image.content.lower() != "n/a" else None
            link = await message_wait(ctx, None, "Please insert a link (or N/A if there's none)")
            link = link.content if link.content.lower() != "n/a" else None
            content = None
            if ntype == "Video Of The Week":
                content = await message_wait(ctx, None, "Please insert the video link")
                content = content.content
                
            
        except QuitError as e:
            await e.message.add_reaction("✅")
            return

        embed = Embed(
            title = title.content,
            description = body.content,
            color = color,
            timestamp = datetime.datetime.utcnow()
        )
        
        if link:
            embed.url = link
        embed.set_footer(text=f"Growtube News | Published by {ctx.author}", icon_url=emoji_url)
        if image:
            embed.set_image(url=image)
            
        tasks = [ctx.send(embed=embed)]
        if content:
            tasks.append(ctx.send(content))
        await asyncio.gather(*tasks, ctx.send("Are you sure? (`yes, y, no, n`)"))
        confirmation = await self.bot.wait_for("message", check=lambda x: x.author == ctx.author and ctx.channel == x.channel and x.content.lower() in {"yes","y","no","n"})
        if confirmation.content.lower().startswith("n"):
            await ctx.send("Cancelled!")
            return
        tasks = [broadcast(chtype, ctx, embed=embed)]
        if content:
            tasks.append(broadcast(chtype, ctx, content))
        await asyncio.gather(*tasks, confirmation.add_reaction("✅"))



def setup(bot: commands.Bot):
    bot.add_cog(Articles(bot))
    print("Loaded articles")
