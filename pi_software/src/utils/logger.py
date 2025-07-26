import logging
import colorlog

from ..config.settings import Config

def setup_logger(name: str) -> logging.Logger:
    """
    Sets up a colorized logger.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(Config.LOG_LEVEL)
        handler = colorlog.StreamHandler()
        formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s - %(message)s',
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger