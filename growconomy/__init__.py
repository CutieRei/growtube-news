from .market import setup as market_setup
from .trading import setup as trading_setup
from .career import setup as career_setup
from bot import GrowTube


def setup(bot: GrowTube):
    market_setup(bot)
    trading_setup(bot)
    career_setup(bot)
