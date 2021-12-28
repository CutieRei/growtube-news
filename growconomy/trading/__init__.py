from .core import Trading
from bot import GrowTube


def setup(bot: GrowTube):
    bot.add_cog(Trading(bot))
    bot.log.info(f"Loaded {__package__}")
