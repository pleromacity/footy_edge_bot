"""
Centralized logging. Every module that can fail silently in the background
(scans, grading, calibration, the scheduler) logs through this, so if
something breaks overnight you can check logs/app.log instead of guessing.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_configured = False


def setup_logging() -> logging.Logger:
    global _configured
    logger = logging.getLogger("footy_edge_bot")

    if _configured:
        return logger

    os.makedirs("logs", exist_ok=True)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler("logs/app.log", maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    _configured = True
    return logger
