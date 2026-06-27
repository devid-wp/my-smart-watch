"""Единая настройка логирования. Вызывается один раз из main()."""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Настройка root-логгера: формат + уровень + stderr."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    # OpenCV шумит в INFO — приглушаем
    logging.getLogger("cv2").setLevel(logging.WARNING)