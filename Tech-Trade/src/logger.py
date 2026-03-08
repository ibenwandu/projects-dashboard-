"""
Logging setup for Tech-Trade
"""

import logging
import colorlog
import sys

def setup_logger(name: str = "Tech-Trade", level: int = logging.INFO) -> logging.Logger:
    """
    Set up colored logger
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler with colors
    handler = colorlog.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter
    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s%(reset)s: %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

