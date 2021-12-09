from discord.ext import commands
from tabulate import tabulate
from bot import GrowTube
import asyncio
import threading
import discord
import psutil
import humanize
import os
import multiprocessing


class Utility(commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def sql(self, ctx, *, query):
        query = query.strip("```") if query.startswith("```") else query
        try:
            records = await self.bot.pool.fetch(query)
            if not records:
                return await ctx.send("0 row")
            headers = records[0].keys()
            await ctx.reply(
                "```\n"
                + tabulate((i.values() for i in records), headers, tablefmt="psql")
                + "```"
            )
        except Exception as e:
            await ctx.send(e)

    @commands.command()
    async def uptime(self, ctx):
        time = discord.utils.utcnow() - self.bot.uptime
        time = humanize.precisedelta(time, format="%d")
        await ctx.send(f"Bot has been up for **{time}**")

    @commands.command()
    async def info(self, ctx):
        embed = discord.Embed(color=self.bot.EMBED_COLOUR)
        python_proc = psutil.Process(os.getpid())
        meminfo = python_proc.memory_info()
        uptime = discord.utils.utcnow() - self.bot.uptime
        uptime = humanize.precisedelta(uptime, minimum_unit="microseconds")
        value = (
            "```"
            f"Memory Usage: {meminfo.rss / (1024 ** 2):.2f}MiB\n"
            f"Virtual Memory Usage: {meminfo.vms / (1024 ** 2):.2f}MiB\n"
            f"Threads: {len(threading.enumerate())}\n"
            f"Child Processes: {len(multiprocessing.active_children())}\n"
            f"Tasks: {len(asyncio.all_tasks())}\n"
            f"Lib: {discord.__name__}=={discord.__version__} by {discord.__author__}\n"
            f"Uptime: {uptime}\n"
            "```"
        )
        embed.add_field(
            name="Bot Usage",
            value=value,
        )
        virtual_memory = psutil.virtual_memory()
        cpus_percent = "\n".join(
            [
                f"\t[{index}] {p}%"
                for index, p in enumerate(psutil.cpu_percent(percpu=True))
            ]
        )
        value = (
            "```"
            f"Available Memory: {virtual_memory.available / (1024 ** 2):.2f} MiB\n"
            f"Used Memory: {virtual_memory.used / (1024 ** 2):.2f} MiB\n"
            f"Free Memory: {virtual_memory.free / (1024 ** 2):.2f} MiB\n"
            f"Cpu Usages: \n{cpus_percent}\n"
            f"Cpu Frequency (total): {psutil.cpu_freq().current} MHz\n"
            "```"
        )
        embed.add_field(
            name="System Info",
            value=value,
        )
        await ctx.send(embed=embed)


def setup(bot: GrowTube) -> None:
    bot.add_cog(Utility(bot))
    bot.log.info(f"Loaded {__file__}")
