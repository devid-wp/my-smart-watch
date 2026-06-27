"""Acceptance-тест Phase 3: добавление нового модуля без правок pipeline/main.

Определяем dummy_module.py здесь же, в тесте, чтобы не загрязнять src/modules
тестовым мусором. Суть: зарегистрировать его через @register_module и проверить,
что build_modules_from_config() собирает инстанс из YAML-подобного dict.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.exceptions import ConfigError
from src.core.interfaces import Frame
from src.core.module_registry import (
    MODULE_REGISTRY,
    build_modules_from_config,
    register_module,
)
from src.modules.base_module import AbstractHUDModule
import time


@register_module("dummy_phase3")
class _DummyPhase3(AbstractHUDModule):
    def __init__(self, name="dummy", enabled=True, marker="default", **kwargs):
        super().__init__(name=name, enabled=enabled, **kwargs)
        self._marker = marker
        self.updated = False

    def update(self, frame, dt):
        self.updated = True

    def render(self, canvas):
        pass


def test_new_module_builds_without_touching_pipeline():
    """Acceptance: новый тип модуля в реестре → build_modules_from_config его собирает."""
    assert "dummy_phase3" in MODULE_REGISTRY
    cfg = [
        {"type": "dummy_phase3", "name": "d1", "enabled": True, "params": {"marker": "x"}},
    ]
    modules = build_modules_from_config(cfg)
    assert len(modules) == 1
    m = modules[0]
    assert m.name == "d1"
    assert m.enabled is True
    assert m._marker == "x"  # type: ignore[attr-defined]


def test_disabled_module_respects_flag():
    cfg = [{"type": "dummy_phase3", "name": "d_off", "enabled": False}]
    m = build_modules_from_config(cfg)[0]
    assert m.enabled is False


def test_unknown_module_type_raises_config_error():
    with pytest.raises(ConfigError, match="Неизвестный modules"):
        build_modules_from_config([{"type": "does_not_exist", "name": "x"}])


def test_missing_module_name_raises_config_error():
    with pytest.raises(ConfigError, match="отсутствует 'name'"):
        build_modules_from_config([{"type": "dummy_phase3"}])


def test_missing_module_type_raises_config_error():
    with pytest.raises(ConfigError, match="отсутствует 'type'"):
        build_modules_from_config([{"name": "x"}])


def test_module_update_runs_without_error():
    """update() не должен бросать на минимальном фрейме."""
    m = build_modules_from_config([{"type": "dummy_phase3", "name": "d"}])[0]
    frame = Frame(image=np.zeros((10, 10, 3), dtype=np.uint8), timestamp=time.monotonic(), frame_id=1)
    m.update(frame, dt=0.016)
    assert m.updated is True  # type: ignore[attr-defined]"""