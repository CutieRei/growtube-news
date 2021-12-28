from .core import Market
from bot import GrowTube


def setup(bot: GrowTube):
    bot.add_cog(Market(bot))
    bot.log.info(f"Loaded {__package__}")
