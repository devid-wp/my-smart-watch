"""ClockModule: текущее время в правом верхнем углу.

Простой модуль без зависимостей — образец для тестов и smoke-демо.
"""

from __future__ import annotations

import time

import cv2

from src.core.interfaces import Frame
from src.core.module_registry import register_module
from src.modules.base_module import AbstractHUDModule


@register_module("clock")
class ClockModule(AbstractHUDModule):
    def __init__(
        self,
        name: str = "clock",
        enabled: bool = True,
        position: tuple[int, int] = (1100, 30),
        color: tuple[int, int, int] = (0, 255, 0),
        font_scale: float = 0.7,
        thickness: int = 2,
        **kwargs,
    ) -> None:
        super().__init__(name=name, enabled=enabled, **kwargs)
        self._position = position
        self._color = color
        self._font_scale = font_scale
        self._thickness = thickness
        self._text = "--:--:--"

    def update(self, frame: Frame, dt: float) -> None:
        # Один раз в кадр пересчитываем строку — дёшево
        self._text = time.strftime("%H:%M:%S")

    def render(self, canvas) -> None:
        cv2.putText(
            canvas,
            self._text,
            self._position,
            cv2.FONT_HERSHEY_SIMPLEX,
            self._font_scale,
            self._color,
            self._thickness,
        )