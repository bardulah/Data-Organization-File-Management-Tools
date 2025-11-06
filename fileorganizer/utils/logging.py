"""
Logging configuration and utilities.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# Create logs directory in user's home
LOG_DIR = Path.home() / '.fileorganizer' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    verbose: bool = False
) -> logging.Logger:
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Custom log file path (defaults to timestamped file)
        verbose: Enable verbose console output

    Returns:
        Configured logger instance
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # File handler - always enabled, detailed logging
    if log_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = LOG_DIR / f'fileorganizer_{timestamp}.log'
    else:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Always log debug to file
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Console handler - configurable
    console_handler = logging.StreamHandler(sys.stdout)
    if verbose:
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(detailed_formatter)
    else:
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        console_handler.setFormatter(simple_formatter)

    root_logger.addHandler(console_handler)

    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Log file: {log_file}")
    logger.debug(f"Log level: {log_level}, Verbose: {verbose}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Name of the module/logger

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class OperationLogger:
    """Context manager for logging operations with success/failure."""

    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        """
        Initialize operation logger.

        Args:
            operation: Description of the operation
            logger: Logger instance (defaults to root logger)
        """
        self.operation = operation
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None

    def __enter__(self):
        """Start operation logging."""
        self.start_time = datetime.now()
        self.logger.info(f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End operation logging."""
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.info(f"Completed: {self.operation} (took {duration:.2f}s)")
        else:
            self.logger.error(
                f"Failed: {self.operation} (took {duration:.2f}s) - {exc_type.__name__}: {exc_val}"
            )

        return False  # Don't suppress exceptions


def log_operation(func):
    """Decorator to log function operations."""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        operation = f"{func.__name__}({', '.join(str(a) for a in args[:2])}...)"

        with OperationLogger(operation, logger):
            return func(*args, **kwargs)

    return wrapper
