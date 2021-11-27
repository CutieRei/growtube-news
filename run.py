import click
import logging
from bot import get_bot

logger = logging.getLogger("bot")

@click.command()
@click.option("--use-color", "--use-colour", "-c", type=bool, default=True)
@click.option("-l", "--event-loop", type=click.Choice(["asyncio", "uvloop"], False), default="best")
def main(use_color: bool, event_loop: str):
    if event_loop.lower() == "uvloop":
        logger.debug("Using 'uvloop'")
        import uvloop # type: ignore
        uvloop.install()
    elif event_loop == "best":
        try:
            logger.debug("Trying 'uvloop'")
            import uvloop # type: ignore
            uvloop.install()
        except ImportError:
            logger.debug("'uvloop' failed (module not installed), falling back to 'asyncio'")

    bot, token = get_bot(use_colour=use_color)
    bot.run(token)


if __name__ == "__main__":
    main()
