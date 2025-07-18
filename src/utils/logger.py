import logging
import os
import colorlog

from config.settings import Config

def setup_logger(name: str) -> logging.Logger:
    """
    Set up a logger with colored output.
    """
    logger = logging.getLogger(name)
    logger.setLevel(Config.LOG_LEVEL)
    logger.propagate = False  # Prevent duplicate logs in parent loggers

    if not logger.hasHandlers():
        handler = colorlog.StreamHandler()
        
        formatter = colorlog.ColoredFormatter(
            fmt='%(log_color)s%(asctime)s [%(levelname)s] %(purple)s[%(name)s]%(reset)s %(message)s',
            datefmt='%H:%M:%S',
            reset=True,
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            },
            style='%'
        )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
