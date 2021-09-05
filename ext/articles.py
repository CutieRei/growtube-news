import aiohttp
from discord.ext import commands
import datetime
from typing import Dict, Optional, Tuple
from discord.ext.commands.errors import NoPrivateMessage
from discord.webhook.async_ import Webhook
import humanize
import asyncio
from discord import Embed, Color, TextChannel, Guild
from bot import GrowTube
from discord import utils
from bot import NotPermittedForPublish

def from_hex(string):
    string = string.replace("#", "0x")
    return Color(int(string, 16))
emoji_url = "https://cdn.discordapp.com/emojis/803865449694494742.png"

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
news_types = {
    "growtopia news": ("Growtopia News", from_hex("#239e1b"), Channel.category1),
    "growtopia announcement": ("Growtopia Announcement", from_hex("#67e85f"), Channel.category1),
    "growtube announcement": ("Growtube Announcement", from_hex("#ffffff"), Channel.category1),
    "wotd": ("World Of The Day", from_hex("#f7e91b"), Channel.category2),
    "votw": ("Video Of The Week", from_hex("#ffffff"), Channel.category2),
    "forums": ("Community Forums", from_hex("#10eb90"), Channel.category3),
    "guidebook": ("Community Guidebook", from_hex("#eb8810"), Channel.category3),
    "suggestions": ("Community Suggestions", from_hex("#0a22f7"), Channel.category3)
}

server_status = {
    "Online": ("Server is online", "<:gtonline:874224931188146216>", Color.green()),
    "Maintenance": ("Server is on maintenance", "<:gtbusy:874224931230060604>", Color.red()),
    "Extended Maintenance": ("The maintenance is extended", "<:gtaway:874224931389472778>", Color.gold())
}

class QuitError(Exception):
    
    def __init__(self, msg=None, message=None):
        self.msg = msg or ""
        self.message = message

    def __str__(self):
        return self.msg

async def message_wait(ctx, predicate, input, msg="Invalid value!"):
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

async def broadcast(chtype, ctx, *args, **kwargs):
    bot: GrowTube = ctx.bot
    channels: Dict[int, Tuple[int, int, int]] = await bot.db.get(str(chtype))

    async with aiohttp.ClientSession() as session:
        async def _send(webhook_data: Tuple[int, int]):
            try:
                webhook = Webhook.partial(webhook_data[0], webhook_data[1], session=session)
                await webhook.send(*args, **kwargs, username=bot.user.name, avatar_url=bot.user.avatar.url)
            except Exception as e:
                print(repr(e))

        tasks = [asyncio.create_task(_send(i[1][1:])) for i in channels.items()]
        if not tasks:
            return
        return await asyncio.wait(tasks)
    
def get_time():
    return datetime.datetime.utcnow() - datetime.timedelta(hours=4)

async def _setchannel(ctx, chtype, channel_id, webhook_id) -> bool:

    bot: GrowTube = ctx.bot
    channel: TextChannel = ctx.guild.get_channel(channel_id)
    if webhook_id is None:
        webhook: Webhook = await channel.create_webhook(name="GrowTube News")
    else:
        webhook: Webhook = utils.get(await channel.webhooks(), id=webhook_id)
        if not webhook:
            return False
    
    guild_id: int = ctx.guild.id
    channels: Dict[int, Dict[int, Tuple[int, int, int]]] = await bot.db.get(str(chtype))
    channels[guild_id] = (channel_id, webhook.id, webhook.token)
    await bot.db.set(chtype, channels)
    return True

def check(ctx: commands.Context):
    if not ctx.guild:
        raise NoPrivateMessage()
    elif not (ctx.author.guild_permissions.manage_channels or ctx.author.get_role(admin_id)):
        raise NotPermittedForPublish("You are not permitted to access the news configuration!")
    return True

class Articles(commands.Cog):

    bot: GrowTube

    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @commands.check(check)
    async def setchannel(self, ctx: commands.Context):
        """
        Set a specific type of news to be sent on a channel.
        If this command is called without any argument, it show's all the channel this server is attached to.
        """
        channels: Dict[int, Dict[int, Tuple[int, int, int]]] = dict(await self.bot.db.items())
        guild: Guild = ctx.guild
        to_render = set()
        for key, value in _channel_dict.items():
            channel = channels[str(key)].get(guild.id)
            if channel:
                channel = guild.get_channel(channel[0])
                channel = channel.mention
            else:
                channel = "none"
            to_render.add(f"{value}: {channel}")

        embed = Embed(
            title = "Attached channels",
            description = "\n".join(to_render),
            color = embed_color,
            timestamp =  datetime.datetime.utcnow()
        )
        await ctx.send(embed=embed)
        
    @setchannel.command()
    async def announcement(self, ctx, channel: TextChannel, webhook: Optional[int] = None):
        """
        Set `Growtopia Announcement, Growtopia News, Growtube News` news to be sent to this channel.
        """
        if not await _setchannel(ctx, Channel.category1, channel.id, webhook):
            return await ctx.send("Webhook not found!")
        await ctx.send(f"Successfully set announcement channel to {channel.mention}")

    @setchannel.command()
    async def contest(self, ctx, channel: TextChannel, webhook: Optional[int] = None):
        """
        Set `VOTW, WOTD` news to be sent to this channel.
        """
        if not await _setchannel(ctx, Channel.category2, channel.id, webhook):
            return await ctx.send("Webhook not found!")
        await ctx.send(f"Successfully set contest news channel to {channel.mention}")

    @setchannel.command()
    async def community(self, ctx, channel: TextChannel, webhook: Optional[int] = None):
        """
        Set Growtopia Community `Forums, Guidebook, Suggestions` news to be sent to this channel.
        """
        if not await _setchannel(ctx, Channel.category3, channel.id, webhook):
            return await ctx.send("Webhook not found!")
        await ctx.send(f"Successfully set community news channel to {channel.mention}")

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

# TODO: use verbose date specifications instead of just time due to synchronization issue
@commands.command()
@commands.guild_only()
async def _maintenance(ctx, *, description: Optional[str] = None):
    embed = Embed(
        title = "Choose server status",
        description = "\n".join([
            f"{value[1]}: {key}" for key, value in server_status.items()
        ])
    )
    msg = await ctx.send(embed=embed)
    await asyncio.gather(*[msg.add_reaction(value[1]) for value in server_status.values()])
    reaction, _ = await ctx.bot.wait_for("reaction_add", check=(lambda r,m: m == ctx.author))
    item = None
    for key, value in server_status.items():
        if value[1] == str(reaction):
            item = (key, value)
            break

    def _parse_time(x):
        try:
            return datetime.datetime.strptime(x.content, "%H:%M")
        except Exception as e:
            return False
    
    try:
        time = await message_wait(ctx, _parse_time, "When did it start? (`HOUR:MINUTE` format in Growtopia time)")
    except QuitError as e:
        await e.message.add_reaction("👍")
    
    await ctx.send("Are you sure? (yes | no)")
    msg = await ctx.bot.wait_for("message", check = lambda x: x.author == ctx.author and x.channel == ctx.channel and x.content.lower() in ["yes", "no"])
    if msg.content.lower() == "no":
        await msg.add_reaction("👍")
        return
    embed = Embed(
        color = item[1][2]
    )
    if description:
        embed.description = description

    time = time.content.split(":")
    time = get_time().replace(
        hour = int(time[0]),
        minute = int(time[1])
    ).strftime("%H:%M")
    embed.set_author(
        icon_url = "https://cdn.discordapp.com/emojis/"+item[1][1].split(":")[-1].strip(">"),
        name = item[1][0] + f" | {time} Growtopia Time"
    )
    embed.set_footer(icon_url = emoji_url, text = f"Growtube News | Published by {ctx.author}")
    await broadcast(Channel.category1, ctx, embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(Articles(bot))
    print("Loaded articles")