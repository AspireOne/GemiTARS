import logging
import os

from config.settings import Config

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(Config.LOG_LEVEL)

    if not logger.hasHandlers():  # Avoid duplicate handlers
        ch = logging.StreamHandler()
        ch.setLevel(Config.LOG_LEVEL)

        formatter = logging.Formatter(
            fmt='[%(levelname)s] %(asctime)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger
