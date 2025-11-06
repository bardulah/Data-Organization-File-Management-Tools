"""
Production logging setup for file organizer.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(verbose: bool = False, log_file: str = None):
    """
    Setup logging for production use.

    Args:
        verbose: Enable verbose console output
        log_file: Custom log file path
    """
    # Create logs directory
    log_dir = Path.home() / '.fileorganizer' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    # Default log file with timestamp
    if log_file is None:
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f'fileorganizer_{timestamp}.log'

    # Configure root logger
    logger = logging.getLogger('fileorganizer')
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    logger.handlers.clear()

    # File handler - always logs everything
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler - configurable
    console_handler = logging.StreamHandler(sys.stdout)
    if verbose:
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    else:
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter('%(message)s')

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized - Log file: {log_file}")

    return logger


def get_logger(name: str = 'fileorganizer'):
    """Get logger instance."""
    return logging.getLogger(name)
