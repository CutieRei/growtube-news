from .core import *
from .trading import *
from bot import GrowTube
from . import utils
from . import career


def setup(bot: GrowTube) -> None:
    bot.add_cog(Growconomy(bot))
    bot.log.info(f"Loaded {__package__}")
