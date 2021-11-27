import logging
import sys
import click
from copy import copy
from typing import Optional

COLOURED_LEVEL = {
    logging.NOTSET: "{}".format(click.style("LOG", fg="bright_white")),
    logging.DEBUG: "{}".format(click.style("DEBUG", fg="bright_green")),
    logging.INFO: "{}".format(click.style("INFO", fg="bright_blue")),
    logging.WARNING: "{}".format(click.style("WARNING", fg="yellow")),
    logging.ERROR: "{}".format(click.style("ERROR", fg="red")),
    logging.CRITICAL: "{}".format(click.style("CRITICAL", fg=(255, 40, 40))),
}


class ColouredFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = "%",
        use_colours: Optional[bool] = None,
    ):
        if use_colours is None:
            self.use_colours = sys.stdout.isatty()
        else:
            self.use_colours = use_colours
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def formatMessage(self, record: logging.LogRecord):
        copied: logging.LogRecord = copy(record)
        if self.use_colours:
            levelname = COLOURED_LEVEL[copied.levelno]
            copied.__dict__["levelname"] = levelname
        return super().formatMessage(copied)


class ClickStreamHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            click.echo(msg + self.terminator, nl=False, file=self.stream)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)
