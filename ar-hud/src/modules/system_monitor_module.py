"""SystemMonitorModule: CPU/RAM и счётчик FPS на базе dt.

Демонстрирует работу с dt (среднее по окну) и IO через psutil.
"""

from __future__ import annotations

import cv2

from src.core.interfaces import Frame
from src.core.module_registry import register_module
from src.modules.base_module import AbstractHUDModule


@register_module("system_monitor")
class SystemMonitorModule(AbstractHUDModule):
    def __init__(
        self,
        name: str = "system_monitor",
        enabled: bool = True,
        position: tuple[int, int] = (20, 30),
        update_interval_sec: float = 1.0,
        **kwargs,
    ) -> None:
        super().__init__(name=name, enabled=enabled, **kwargs)
        self._position = position
        self._update_interval = update_interval_sec
        self._since_update = 0.0
        self._dt_window: list[float] = []
        self._fps: float = 0.0
        self._cpu: float = 0.0
        self._ram: float = 0.0
        # import внутри __init__, чтобы модуль импортировался даже без psutil — но мы его ставим в Phase 0
        import psutil  # noqa: WPS433 — намеренно ленивый импорт

        self._psutil = psutil

    def update(self, frame: Frame, dt: float) -> None:
        self._dt_window.append(dt)
        if len(self._dt_window) > 30:
            self._dt_window.pop(0)
        self._since_update += dt
        if self._since_update >= self._update_interval:
            self._since_update = 0.0
            if self._dt_window:
                avg = sum(self._dt_window) / len(self._dt_window)
                self._fps = 1.0 / avg if avg > 0 else 0.0
            self._cpu = self._psutil.cpu_percent(interval=None)
            self._ram = self._psutil.virtual_memory().percent

    def render(self, canvas) -> None:
        x, y = self._position
        cv2.putText(
            canvas,
            f"FPS: {self._fps:5.1f}",
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 0),
            1,
        )
        cv2.putText(
            canvas,
            f"CPU: {self._cpu:5.1f}%",
            (x, y + 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            1,
        )
        cv2.putText(
            canvas,
            f"RAM: {self._ram:5.1f}%",
            (x, y + 44),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            1,
        )