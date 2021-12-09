from .core import *
from .trading import *
from bot import GrowTube

def setup(bot: GrowTube) -> None:
    bot.add_cog(Growconomy(bot))
    bot.log.info(f"Loaded {__name__}")
