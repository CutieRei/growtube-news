from .core import Career
from bot import GrowTube


def setup(bot: GrowTube):
    bot.add_cog(Career(bot))
    bot.log.info(f"Loaded {__package__}")
