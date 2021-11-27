import click
from bot import get_bot


@click.command()
@click.option("--use-color", "--use-colour", "-c", type=bool, default=True)
def main(use_color: bool):
    bot, token = get_bot(use_colour=use_color)
    if use_color:
        try:
            import colorama

            with colorama.colorama_text():
                return bot.run(token)
        except ImportError:
            import sys

            if sys.platform.startswith("win"):
                bot.log.warning("'colorama' not installed, not using colour")
    bot.run(token)


if __name__ == "__main__":
    main()
