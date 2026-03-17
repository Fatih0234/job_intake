"""Minimal stdout logging setup."""

from __future__ import annotations

import logging
import sys

from job_intake.settings import Settings, get_settings


def configure_logging(settings: Settings | None = None) -> None:
    active_settings = settings or get_settings()
    logging.basicConfig(
        level=getattr(logging, active_settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
