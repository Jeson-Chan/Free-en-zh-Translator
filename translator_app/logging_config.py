"""Logging helpers for the desktop application."""

from __future__ import annotations

import logging
from pathlib import Path

from translator_app.constants import LOG_FILE_NAME


def configure_logging(root_path: Path) -> None:
    """Configure application logging to file and stderr."""
    log_path = root_path / LOG_FILE_NAME

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

