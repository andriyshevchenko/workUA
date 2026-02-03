"""Logging configuration module"""

import logging
from datetime import datetime
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Setup logging to console and file

    Returns:
        Configured root logger
    """
    logger = logging.getLogger()

    # Check if handlers are already configured to avoid duplicates
    if logger.handlers:
        return logger

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"workua_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Log format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Configure root logger
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
