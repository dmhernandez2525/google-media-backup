"""
Logging configuration for Google Media Backup.
Provides dual logging to console and file with immediate flush.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .paths import Paths


class FlushingFileHandler(logging.FileHandler):
    """File handler that flushes after every write for real-time logs."""
    def emit(self, record):
        super().emit(record)
        self.flush()


class FlushingStreamHandler(logging.StreamHandler):
    """Stream handler that flushes after every write."""
    def emit(self, record):
        super().emit(record)
        self.flush()


# Module-level logger instance
_logger: Optional[logging.Logger] = None


def get_logger(name: str = "GoogleMediaBackup") -> logging.Logger:
    """
    Get or create the application logger.

    Returns a logger that outputs to both console and file.
    Logs are flushed immediately for real-time visibility.
    """
    global _logger

    if _logger is not None:
        return _logger

    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers if called multiple times
    if _logger.handlers:
        return _logger

    # Console handler - INFO level (with immediate flush)
    console_handler = FlushingStreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    _logger.addHandler(console_handler)

    # File handler - DEBUG level (with immediate flush)
    try:
        log_file = Paths.get_log_file()
        file_handler = FlushingFileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        _logger.addHandler(file_handler)
        _logger.info(f"Logging to: {log_file}")
    except Exception as e:
        _logger.warning(f"Could not create file handler: {e}")

    return _logger


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """Log an exception with full traceback."""
    logger.error(f"{message}: {exc}", exc_info=True)
