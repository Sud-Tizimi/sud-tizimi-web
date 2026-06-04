"""Plain stdlib logging config — easy to read in dev, no extra deps."""
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
        stream=sys.stdout,
        force=True,
    )
    # Quiet down very chatty libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
