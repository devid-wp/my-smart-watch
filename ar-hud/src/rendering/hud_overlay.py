"""HUDOverlay — оркестратор update()/render() зарегистрированных модулей.

Не рисует сама. Разделяет фазы update и render, чтобы их частоты в будущем
можно было развести (логика 60 Гц, дисплей AR-устройства — другая).
"""

from __future__ import annotations

import numpy as np

from src.core.interfaces import Frame, IHUDModule


class HUDOverlay:
    """Список модулей + единая точка обновления/отрисовки."""

    def __init__(self, modules: list[IHUDModule]) -> None:
        self._modules = list(modules)

    @property
    def modules(self) -> list[IHUDModule]:
        return self._modules

    def update(self, frame: Frame, dt: float) -> None:
        for m in self._modules:
            if m.enabled:
                m.update(frame, dt)

    def render(self, canvas: np.ndarray) -> None:
        for m in self._modules:
            if m.enabled:
                m.render(canvas)