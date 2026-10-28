"""Shared logging setup for the project."""

import logging

LOGGER_NAME = "railway_delay"


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Return a logger, configuring the root project logger on first use."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
