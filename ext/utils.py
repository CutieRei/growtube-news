import asyncio
import threading
import discord
import psutil
import humanize
import os
import multiprocessing
from discord.ext import commands
from datetime import datetime
from bot import GrowTube


class Utility(commands.Cog):
    def __init__(self, bot: GrowTube) -> None:
        self.bot = bot

    @commands.commands()
    async def uptime(self, ctx):
        time = datetime.utcnow() - self.bot.uptime
        await ctx.send(f"Bot has been up for **{humanize.precisedelta(time)}**")

    @commands.command()
    async def info(self, ctx):
        embed = discord.Embed(color=discord.Color.random())
        python_proc = psutil.Process(os.getpgid())
        meminfo = python_proc.memory_info()
        uptime = datetime.utcnow() - self.bot.uptime
        embed.add_field(
            "Bot Usage",
            f"""
            Memory Usage: {meminfo.rss / (1024 ** 2):.2f}MiB
            Virtual Memory Usage: {meminfo.vms / (1024 ** 2):.2f}MiB
            Threads: {len(threading.enumerate)}
            Processes: {len(multiprocessing.active_children())}
            Tasks: {len(asyncio.all_tasks())}
            Lib: {discord.__name__}=={discord.__version__} by {discord.__author__}
            Uptime: {humanize.precisedelta(uptime)}
            """,
        )
        virtual_memory = psutil.virtual_memory()
        cpus_percent = "\n".join(
            [
                f"[{index}] {p}%"
                for index, p in enumerate(psutil.cpu_percent(percpu=True))
            ]
        )
        embed.add_field(
            "System Info",
            f"""
        Available Memory: {virtual_memory.available}
        Used Memory: {virtual_memory.used}
        Free Memory: {virtual_memory.free}
        Cpu Usages: 
            {cpus_percent}
        Cpu Frequency (total): {psutil.cpu_freq()}
        """,
        )
        await ctx.send(embed=embed)


def setup(bot: GrowTube) -> None:
    bot.add_cog(Utility(bot))
    bot.log.info(f"Loaded {__file__}")
