"""Реестр модулей по имени из конфига + фабрика инстансов.

Использование:
    @register_module("clock")
    class ClockModule(AbstractHUDModule): ...

    modules = build_modules_from_config(cfg.modules)
"""

from __future__ import annotations

from src.core.exceptions import ConfigError
from src.core.interfaces import IHUDModule
from src.modules.base_module import AbstractHUDModule


# Глобальный реестр: key (из YAML type) → класс
MODULE_REGISTRY: dict[str, type[AbstractHUDModule]] = {}


def register_module(key: str):
    """Декоратор. Регистрирует класс под именем key, чтобы YAML type: key находил его."""

    def decorator(cls: type[AbstractHUDModule]) -> type[AbstractHUDModule]:
        if key in MODULE_REGISTRY:
            raise ValueError(f"Модуль с ключом {key!r} уже зарегистрирован")
        MODULE_REGISTRY[key] = cls
        return cls

    return decorator


def build_modules_from_config(cfg: list[dict]) -> list[IHUDModule]:
    """Сконструировать модули из секции modules конфига.

    Каждая запись cfg:
        - type: str (ключ в MODULE_REGISTRY)
        - name: str (имя инстанса)
        - enabled: bool (опц., default True)
        - params: dict (опц., kwargs для __init__)
    """
    # Локальный импорт, чтобы избежать циклических импортов при регистрации
    from src.modules import (
        clock_module,
        face_detection_module,
        system_monitor_module,
        weather_module,
    )

    # noqa: F401 — модули нужны только как side-effect (регистрация через декоратор)
    modules: list[IHUDModule] = []
    for entry in cfg:
        if "type" not in entry:
            raise ConfigError(f"modules[*]: отсутствует 'type'. Запись: {entry!r}")
        if "name" not in entry:
            raise ConfigError(f"modules[*]: отсутствует 'name'. Запись: {entry!r}")
        ctype = entry["type"]
        cls = MODULE_REGISTRY.get(ctype)
        if cls is None:
            raise ConfigError(
                f"Неизвестный modules[*].type: {ctype!r}. "
                f"Зарегистрированы: {sorted(MODULE_REGISTRY)}"
            )
        modules.append(
            cls(
                name=entry["name"],
                enabled=entry.get("enabled", True),
                **entry.get("params", {}),
            )
        )
    return modules