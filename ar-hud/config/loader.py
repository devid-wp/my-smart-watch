"""Загрузка и валидация YAML-конфига через Pydantic."""

from __future__ import annotations

from pathlib import Path

import yaml

from config.schema import AppConfig
from src.core.exceptions import ConfigError


def load_config(path: str | Path) -> AppConfig:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Конфиг не найден: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ConfigError(f"Невалидный YAML в {p}: {e}") from e
    if not isinstance(raw, dict):
        raise ConfigError(f"Конфиг должен быть мапой на верхнем уровне, не {type(raw).__name__}")
    try:
        return AppConfig(**raw)
    except Exception as e:
        raise ConfigError(f"Конфиг не прошёл валидацию: {e}") from e