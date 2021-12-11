from asyncio import wait, FIRST_COMPLETED
from typing import Awaitable
from discord.ext import commands
from bot import GrowTube


async def async_any(*aws: Awaitable, cancel=True):
    done, pending = await wait(aws, return_when=FIRST_COMPLETED)
    if cancel:
        for fut in pending:
            fut.cancel()
    (done,) = done
    return done


GrowContext = commands.Context[GrowTube]
