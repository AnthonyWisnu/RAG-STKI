"""Utility logging untuk backend dan ETL."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_level: str = "INFO", log_file: Path | None = None) -> None:
    """Mengatur logging konsisten untuk script backend.

    Args:
        log_level: Level logging seperti INFO, WARNING, atau ERROR.
        log_file: Path file log opsional.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )

