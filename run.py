import click
from bot import get_bot


@click.command()
@click.option("--use-color", "--use-colour", "-c", type=bool, default=True)
@click.option(
    "-l",
    "--event-loop",
    type=click.Choice(["asyncio", "uvloop", "best"], False),
    default="best",
)
def main(use_color: bool, event_loop: str):
    bot, token = get_bot(use_colour=use_color)
    if event_loop.lower() == "uvloop":
        bot.log.debug("Using 'uvloop'")
        import uvloop  # type: ignore

        uvloop.install()
    elif event_loop.lower() == "best":
        try:
            bot.log.debug("Trying 'uvloop'")
            import uvloop  # type: ignore

            uvloop.install()
            bot.log.debug("Using uvloop")
        except ImportError:
            bot.log.debug(
                "'uvloop' failed (module not installed), falling back to 'asyncio'"
            )

    bot.run(token)


if __name__ == "__main__":
    main()
