"""
Centralized logging configuration for the VPP application.

Development  → coloured human-readable output to stdout.
Production   → JSON output to stdout (machine-parseable for ELK/Loki/CloudWatch).

Public API is unchanged: call get_logger(__name__) in any module.
"""

import logging
import os
import sys
from typing import Optional

from pythonjsonlogger import jsonlogger


class ColoredFormatter(logging.Formatter):
    """Human-readable coloured formatter for local development."""

    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: blue + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)

    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    if _is_production():
        fmt = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
        )
    else:
        fmt = ColoredFormatter()

    handler.setFormatter(fmt)
    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    return setup_logger(name)
