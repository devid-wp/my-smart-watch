"""Главный цикл. Связывает камеру + оверлей + дисплей. Не знает про конкретные модули."""

from __future__ import annotations

import logging
from typing import Protocol

import numpy as np

from src.core.clock import Clock
from src.core.interfaces import ICameraSource
from src.rendering.hud_overlay import HUDOverlay


logger = logging.getLogger(__name__)


class _DisplayLike(Protocol):
    """Структурный контракт для дисплея. IDisplaySink подходит, но Protocol
    ослабляет связь — pipeline достаточно знать show/close."""

    def show(self, canvas: np.ndarray) -> bool: ...
    def close(self) -> None: ...


class Pipeline:
    """Главный цикл приложения.

    dt считается здесь через Clock.tick() — единственная точка замера.
    Кадр копируется перед отрисовкой, чтобы модули не мутировали Frame.image.
    """

    def __init__(
        self,
        camera: ICameraSource,
        overlay: HUDOverlay,
        clock: Clock,
        display: _DisplayLike,
    ) -> None:
        self._camera = camera
        self._overlay = overlay
        self._clock = clock
        self._display = display
        self._running = False

    def stop(self) -> None:
        """Попросить цикл завершиться на следующей итерации."""
        self._running = False

    def run(self) -> None:
        self._running = True
        self._camera.start()
        try:
            while self._running:
                dt = self._clock.tick()
                frame = self._camera.read()
                if frame is None:
                    # источник ещё не дал кадр — пропускаем итерацию
                    continue

                # canvas — отдельный буфер для модулей, чтобы они не трогали Frame.image
                canvas = frame.image.copy()
                self._overlay.update(frame, dt)
                self._overlay.render(canvas)

                if not self._display.show(canvas):
                    self._running = False
        finally:
            self._camera.stop()
            self._display.close()
            logger.info("Pipeline остановлен")